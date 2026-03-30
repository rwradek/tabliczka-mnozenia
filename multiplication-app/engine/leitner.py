"""
Leitner 5-box system — tracks card progress.

Boxes define frequency of repetition (1 = highest), NOT calendar dates.
Card selection is handled entirely by session_builder.py.
"""


def process_answer(leitner_data: dict, fact_id: str, correct: bool, response_ms: int) -> dict:
    """
    Update a card's box after an answer.
    - Correct → box + 1 (max 5).  First-ever correct goes to box 1.
    - Wrong   → box 1.
    Cards are independent — a wrong answer on 2×3 does not affect 3×2.
    Returns {old_box, new_box}.
    """
    card = leitner_data[fact_id]
    old_box = card["box"]

    if correct:
        new_box = min(old_box + 1, 5) if old_box > 0 else 1
    else:
        new_box = 1

    card["box"] = new_box
    card["history"].append({"correct": correct, "response_ms": response_ms})
    return {"old_box": old_box, "new_box": new_box}
