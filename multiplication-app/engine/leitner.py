"""
Leitner 5-box spaced repetition system.
"""
from datetime import date, timedelta

# Days between reviews for each box number
BOX_INTERVALS = {1: 1, 2: 2, 3: 4, 4: 8, 5: 16}


def process_answer(leitner_data, fact_id, correct, response_ms):
    """
    Update a card's Leitner state after an answer.
    Returns dict with old_box and new_box.
    """
    card = leitner_data[fact_id]
    old_box = card["box"]

    if correct:
        new_box = min(old_box + 1, 5) if old_box > 0 else 1
    else:
        new_box = 1

    card["box"] = new_box
    card["active"] = True
    card["next_review"] = (
        date.today() + timedelta(days=BOX_INTERVALS[new_box])
    ).isoformat()
    card["history"].append(
        {
            "date": date.today().isoformat(),
            "correct": correct,
            "response_ms": response_ms,
        }
    )
    return {"old_box": old_box, "new_box": new_box}


def get_cards_due(leitner_data):
    """Return list of active fact_ids whose next_review is today or earlier."""
    today = date.today().isoformat()
    return [
        fid
        for fid, card in leitner_data.items()
        if card["active"]
        and card["next_review"] is not None
        and card["next_review"] <= today
    ]


def get_new_cards(leitner_data, active_group_ids, groups):
    """Return fact_ids that are active but never yet practiced (box == 0)."""
    result = []
    seen = set()
    for group_id in active_group_ids:
        for fid in groups.get(group_id, []):
            card = leitner_data.get(fid)
            if card and card["active"] and card["box"] == 0 and fid not in seen:
                result.append(fid)
                seen.add(fid)
    return result


def get_known_cards(leitner_data):
    """Return active fact_ids in boxes 3–5, sorted by oldest next_review first."""
    cards = [
        (fid, card)
        for fid, card in leitner_data.items()
        if card["active"] and card["box"] >= 3
    ]
    cards.sort(key=lambda x: x[1]["next_review"] or "0000-00-00")
    return [fid for fid, _ in cards]


def is_mastered(leitner_data, fact_id, mastery_threshold_ms=3000):
    """Return True if card is in box ≥ 4 and last 3 answers averaged < threshold ms."""
    card = leitner_data.get(fact_id, {})
    if card.get("box", 0) < 4:
        return False
    recent = card.get("history", [])[-3:]
    if not recent:
        return False
    avg_ms = sum(h["response_ms"] for h in recent) / len(recent)
    return avg_ms < mastery_threshold_ms


def group_all_in_box_min(leitner_data, group_fact_ids, min_box):
    """Return True if every fact in the group has box >= min_box."""
    return all(
        leitner_data.get(fid, {}).get("box", 0) >= min_box
        for fid in group_fact_ids
    )
