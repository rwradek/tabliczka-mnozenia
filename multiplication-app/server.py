"""
Flask server — routes, session management, auto-save, shutdown handling.
Run: python server.py
"""
import json
import os
import signal
import sys
import time
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from data.facts import (
    FACTS,
    GROUPS,
    INTRODUCTION_ORDER,
    init_leitner_data,
)
from engine.leitner import process_answer
from engine.session_builder import build_session_queue, generate_distractors
from engine.group_selector import suggest_next_group, activate_group

app = Flask(__name__)

DATA_FILE = os.path.join(BASE_DIR, "data", "session_data.json")

# ── In-memory state ─────────────────────────────────────────────────────────
_state: dict = {}
_current_session: dict | None = None
_answers_since_save: int = 0
# ────────────────────────────────────────────────────────────────────────────


def _default_state() -> dict:
    groups_state = {
        g: {"status": "active" if g == "A1" else "pending"}
        for g in INTRODUCTION_ORDER
    }
    return {
        "leitner": init_leitner_data(["A1"]),
        "groups": groups_state,
        "pending_sessions": [],
        "completed_sessions": [],
        "settings": {
            "answer_mode": "keyboard",
            "session_length_min": 12,
            "session_hard_limit_min": 20,
            "new_cards_per_session": 2,
            "autosave_every_n": 5,
            "mastery_threshold_ms": 3000,
        },
        "stats": {
            "total_sessions": 0,
            "total_answers": 0,
            "last_session": None,
        },
    }


def load_state() -> None:
    global _state
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            _state = json.load(fh)
        # Ensure all current FACTS are present (handles data migrations)
        for fid in FACTS:
            if fid not in _state["leitner"]:
                _state["leitner"][fid] = {
                    "box": 0,
                    "next_review": None,
                    "active": False,
                    "history": [],
                }
    else:
        _state = _default_state()
        save_state()


def save_state() -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(_state, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)  # atomic write


def _shutdown_handler(signum, frame) -> None:
    save_state()
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown_handler)
signal.signal(signal.SIGINT, _shutdown_handler)


# ═══════════════════════════════════════════════════════════════════════════
# Child endpoints
# ═══════════════════════════════════════════════════════════════════════════


@app.route("/child/")
def child_index():
    return render_template("child.html")


@app.route("/child/next")
def child_next():
    global _current_session

    if _current_session is None:
        _current_session = _create_session()

    session = _current_session

    # Hard time limit check
    elapsed_min = (time.time() - session["start_time"]) / 60
    hard_limit = _state["settings"].get("session_hard_limit_min", 20)
    if elapsed_min >= hard_limit and not session.get("done"):
        session["done"] = True
        _finalize_session()

    if session.get("done") or session["current_idx"] >= len(session["queue"]):
        return jsonify({"done": True})

    fact_id = session["queue"][session["current_idx"]]
    fact = FACTS[fact_id]
    mode = _state["settings"]["answer_mode"]

    payload: dict = {
        "done": False,
        "fact_id": fact_id,
        "a": fact["a"],
        "b": fact["b"],
        "mode": mode,
        "progress": {
            "done": session["current_idx"],
            "total": len(session["queue"]),
        },
        "time_elapsed_s": int(time.time() - session["start_time"]),
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
    global _current_session, _answers_since_save

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

    result = process_answer(_state["leitner"], fact_id, correct, response_time_ms)

    streak = 0
    if _current_session:
        _current_session["answers_given"] += 1
        _current_session["total_response_ms"] += response_time_ms
        if correct:
            _current_session["correct_count"] += 1
            _current_session["correct_streak"] += 1
        else:
            _current_session["correct_streak"] = 0
        _current_session["current_idx"] += 1
        streak = _current_session["correct_streak"]

        if _current_session["current_idx"] >= len(_current_session["queue"]):
            _current_session["done"] = True
            _finalize_session()

    _state["stats"]["total_answers"] += 1
    _answers_since_save += 1
    if _answers_since_save >= _state["settings"].get("autosave_every_n", 5):
        save_state()
        _answers_since_save = 0

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


# ═══════════════════════════════════════════════════════════════════════════
# Parent endpoints
# ═══════════════════════════════════════════════════════════════════════════


@app.route("/parent/")
def parent_index():
    return render_template("parent.html")


@app.route("/parent/stats")
def parent_stats():
    leitner = _state["leitner"]

    # Full 10×10 grid (1–10), inactive/outside range marked
    grid = {}
    for a in range(1, 11):
        for b in range(1, 11):
            fid = f"{a}x{b}"
            card = leitner.get(fid)
            if card:
                grid[fid] = {"box": card["box"], "active": card["active"]}
            else:
                grid[fid] = {"box": -1, "active": False}  # ×1 / ×10 trivial

    # Box distribution counts
    box_counts = {str(i): 0 for i in range(6)}
    box_next: dict[str, str | None] = {}
    today = date.today().isoformat()
    for card in leitner.values():
        b = str(card["box"])
        box_counts[b] = box_counts.get(b, 0) + 1

    for i in range(1, 6):
        dates = [
            c["next_review"]
            for c in leitner.values()
            if c["box"] == i and c["active"] and c["next_review"]
        ]
        box_next[str(i)] = min(dates) if dates else None

    # Top-5 difficult facts (most errors)
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

    return jsonify(
        {
            "grid": grid,
            "box_counts": box_counts,
            "box_next": box_next,
            "completed_sessions": _state["completed_sessions"][-30:],
            "difficult_facts": difficult[:5],
            "groups": _state["groups"],
            "suggested_group": suggest_next_group(_state),
            "stats": _state["stats"],
        }
    )


@app.route("/parent/settings", methods=["GET", "POST"])
def parent_settings():
    if request.method == "GET":
        return jsonify(_state["settings"])

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    allowed = {
        "answer_mode",
        "session_length_min",
        "session_hard_limit_min",
        "new_cards_per_session",
        "autosave_every_n",
        "mastery_threshold_ms",
    }
    for key, value in data.items():
        if key in allowed:
            _state["settings"][key] = value

    save_state()
    return jsonify({"ok": True, "settings": _state["settings"]})


@app.route("/parent/override-group", methods=["POST"])
def parent_override_group():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    group_id = data.get("group_id", "")
    if group_id not in GROUPS:
        return jsonify({"error": "Unknown group_id"}), 400

    activate_group(_state, group_id)
    save_state()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════
# System endpoints
# ═══════════════════════════════════════════════════════════════════════════


@app.route("/system/save", methods=["POST"])
def system_save():
    save_state()
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════


def _create_session() -> dict:
    active_groups = [
        g for g, info in _state["groups"].items() if info["status"] == "active"
    ]
    queue = build_session_queue(
        _state["leitner"], FACTS, GROUPS, active_groups, _state["settings"]
    )
    return {
        "id": f"s_{date.today().strftime('%Y%m%d')}_{int(time.time())}",
        "queue": queue,
        "current_idx": 0,
        "start_time": time.time(),
        "answers_given": 0,
        "correct_count": 0,
        "correct_streak": 0,
        "total_response_ms": 0,
        "done": False,
    }


def _finalize_session() -> None:
    global _current_session
    s = _current_session
    if not s:
        return
    answers = s["answers_given"]
    correct = s["correct_count"]
    total_ms = s["total_response_ms"]
    avg_ms = total_ms // answers if answers > 0 else 0

    _state["completed_sessions"].append(
        {
            "id": s["id"],
            "completed_at": datetime.now().isoformat(),
            "answers": answers,
            "correct": correct,
            "accuracy": round(correct / answers * 100) if answers > 0 else 0,
            "avg_response_ms": avg_ms,
        }
    )
    _state["stats"]["total_sessions"] += 1
    _state["stats"]["last_session"] = date.today().isoformat()
    save_state()


# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    load_state()
    print("Serwer uruchomiony na http://0.0.0.0:5001")
    print("  Dziecko: http://<IP>:5001/child/")
    print("  Rodzic:  http://<IP>:5001/parent/")
    app.run(host="0.0.0.0", port=5001, debug=False)
