"""
Flask server — routes, session management, save on shutdown.
Run: python server.py
"""
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from data.facts import FACTS, GROUPS, INTRODUCTION_ORDER, init_leitner_data
from engine.leitner import process_answer
from engine.session_builder import (
    BOX_SEQUENCE,
    build_session_queue,
    on_session_finished,
    generate_distractors,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
DATA_FILE = os.path.join(BASE_DIR, "data", "session_data.json")

ST: dict = {}
_current_session: dict | None = None


def _default_state() -> dict:
    return {
        "leitner": init_leitner_data(),
        "scheduler": {
            "phase": "groups",
            "current_group_idx": 0,
            "consecutive_clean": 0,
            "box_seq_idx": 0,
            "current_batch": None,
            "box_copies": {},
        },
        "completed_sessions": [],
        "settings": {"answer_mode": "keyboard"},
        "stats": {"total_sessions": 0, "total_answers": 0},
    }


def load_state() -> None:
    global ST
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            ST = json.load(fh)
        for fid in FACTS:
            if fid not in ST["leitner"]:
                ST["leitner"][fid] = {"box": 0, "history": []}
        if "scheduler" not in ST:
            ST["scheduler"] = _default_state()["scheduler"]
        logger.info("Stan wczytany z %s", DATA_FILE)
    else:
        ST = _default_state()
        save_state()
        logger.info("Nowy stan zainicjalizowany.")


def save_state() -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ST, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


def _shutdown_handler(signum, frame) -> None:
    save_state()
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


# ══════════════════════════ Child ═════════════════════════════════════════


@app.route("/child/")
def child_index():
    return render_template("child.html")


@app.route("/child/next")
def child_next():
    global _current_session
    if _current_session is None:
        _current_session = _create_session()
    s = _current_session
    if s.get("done") or s["current_idx"] >= len(s["queue"]):
        return jsonify({"done": True})
    fact_id = s["queue"][s["current_idx"]]
    fact = FACTS[fact_id]
    mode = ST["settings"]["answer_mode"]
    payload: dict = {
        "done": False,
        "fact_id": fact_id,
        "a": fact["a"],
        "b": fact["b"],
        "mode": mode,
        "progress": {"done": s["current_idx"], "total": len(s["queue"])},
        "time_elapsed_s": int(time.time() - s["start_time"]),
    }
    if mode == "tiles":
        import random

        distractors = generate_distractors(fact_id, FACTS)
        options = distractors + [fact["result"]]
        random.shuffle(options)
        payload["options"] = options
    return jsonify(payload)


@app.route("/child/answer", methods=["POST"])
def child_answer():
    global _current_session
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    fact_id = data.get("fact_id", "")
    if fact_id not in FACTS:
        return jsonify({"error": "Invalid fact_id"}), 400
    try:
        answer = int(data["answer"])
        response_time_ms = int(data["response_time_ms"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid answer or response_time_ms"}), 400
    correct_answer = FACTS[fact_id]["result"]
    correct = answer == correct_answer
    result = process_answer(ST["leitner"], fact_id, correct, response_time_ms)
    ST["stats"]["total_answers"] = ST["stats"].get("total_answers", 0) + 1
    streak = 0
    if _current_session:
        s = _current_session
        s["answers_given"] += 1
        s["total_response_ms"] += response_time_ms
        if correct:
            s["correct_count"] += 1
            s["correct_streak"] += 1
        else:
            s["correct_streak"] = 0
            s["had_error"] = True
        s["current_idx"] += 1
        streak = s["correct_streak"]
        if s["current_idx"] >= len(s["queue"]):
            s["done"] = True
            _finalize_session()
    return jsonify(
        {
            "correct": correct,
            "correct_answer": correct_answer,
            "box_moved_to": result["new_box"],
            "streak": streak,
        }
    )


@app.route("/child/session-status")
def child_session_status():
    if _current_session is None:
        return jsonify({"active": False})
    s = _current_session
    return jsonify(
        {
            "active": True,
            "questions_done": s["current_idx"],
            "questions_total": len(s["queue"]),
            "correct_count": s["correct_count"],
            "time_elapsed_s": int(time.time() - s["start_time"]),
            "done": s.get("done", False),
            "correct_streak": s.get("correct_streak", 0),
        }
    )


@app.route("/child/new-session", methods=["POST"])
def child_new_session():
    global _current_session
    _current_session = _create_session()
    return jsonify({"ok": True, "queue_length": len(_current_session["queue"])})


# ══════════════════════════ Parent ════════════════════════════════════════


@app.route("/parent/")
def parent_index():
    return render_template("parent.html")


@app.route("/parent/stats")
def parent_stats():
    leitner = ST["leitner"]
    grid = {}
    for a in range(1, 11):
        for b in range(1, 11):
            fid = f"{a}x{b}"
            card = leitner.get(fid)
            grid[fid] = {"box": card["box"] if card else -1}
    box_cards: dict[str, list] = {str(i): [] for i in range(6)}
    for fid, card in leitner.items():
        b = str(card["box"])
        f = FACTS.get(fid, {})
        box_cards[b].append(
            {
                "fact_id": fid,
                "a": f.get("a"),
                "b": f.get("b"),
                "result": f.get("result"),
            }
        )
    difficult = []
    for fid, card in leitner.items():
        errors = sum(1 for h in card["history"] if not h["correct"])
        if errors > 0:
            f = FACTS.get(fid, {})
            difficult.append(
                {
                    "fact_id": fid,
                    "a": f.get("a"),
                    "b": f.get("b"),
                    "result": f.get("result"),
                    "errors": errors,
                    "total": len(card["history"]),
                }
            )
    difficult.sort(key=lambda x: -x["errors"])
    sched = ST["scheduler"]
    phase = sched.get("phase", "groups")
    if phase == "groups":
        idx = sched.get("current_group_idx", 0)
        phase_info = {
            "phase": "groups",
            "current_group": (
                INTRODUCTION_ORDER[idx] if idx < len(INTRODUCTION_ORDER) else None
            ),
            "consecutive_clean": sched.get("consecutive_clean", 0),
            "progress": f"{idx}/{len(INTRODUCTION_ORDER)}",
        }
    else:
        seq_idx = sched.get("box_seq_idx", 0) % len(BOX_SEQUENCE)
        phase_info = {
            "phase": "leitner",
            "current_box": BOX_SEQUENCE[seq_idx],
            "consecutive_clean": sched.get("consecutive_clean", 0),
        }
    return jsonify(
        {
            "grid": grid,
            "box_cards": box_cards,
            "completed_sessions": ST["completed_sessions"][-30:],
            "difficult_facts": difficult[:5],
            "phase_info": phase_info,
            "stats": ST["stats"],
        }
    )


@app.route("/parent/settings", methods=["GET", "POST"])
def parent_settings():
    if request.method == "GET":
        return jsonify(ST["settings"])
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    if "answer_mode" in data and data["answer_mode"] in ("keyboard", "tiles"):
        ST["settings"]["answer_mode"] = data["answer_mode"]
    save_state()
    return jsonify({"ok": True, "settings": ST["settings"]})


# ══════════════════════════ System ════════════════════════════════════════


@app.route("/system/save", methods=["POST"])
def system_save():
    save_state()
    return jsonify({"ok": True})


# ══════════════════════════ Helpers ═══════════════════════════════════════


def _create_session() -> dict:
    queue = build_session_queue(ST["leitner"], ST["scheduler"])
    logger.info("Nowa sesja | Kolejka (%d kart): %s", len(queue), queue)
    return {
        "queue": queue,
        "current_idx": 0,
        "start_time": time.time(),
        "answers_given": 0,
        "correct_count": 0,
        "correct_streak": 0,
        "total_response_ms": 0,
        "had_error": False,
        "done": False,
    }


def _finalize_session() -> None:
    global _current_session
    s = _current_session
    if not s:
        return
    answers = s["answers_given"]
    correct = s["correct_count"]
    avg_ms = s["total_response_ms"] // answers if answers > 0 else 0
    all_correct = not s["had_error"]
    ST["completed_sessions"].append(
        {
            "completed_at": datetime.now().isoformat(),
            "answers": answers,
            "correct": correct,
            "accuracy": round(correct / answers * 100) if answers > 0 else 0,
            "avg_response_ms": avg_ms,
        }
    )
    ST["stats"]["total_sessions"] = ST["stats"].get("total_sessions", 0) + 1
    status = "BEZ BLEDOW" if all_correct else f"ERRORS ({answers - correct})"
    logger.info("Sesja zakonczona | %s | %d/%d", status, correct, answers)
    on_session_finished(ST["scheduler"], ST["leitner"], all_correct)
    save_state()


# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    load_state()
    print("Serwer uruchomiony na http://0.0.0.0:5001")
    print("  Dziecko: http://<IP>:5001/child/")
    print("  Rodzic:  http://<IP>:5001/parent/")
    app.run(host="0.0.0.0", port=5001, debug=False)
