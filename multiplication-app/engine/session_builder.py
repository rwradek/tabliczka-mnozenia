"""
Session queue builder using Incremental Rehearsal (8:1 ratio).
Pattern: [known×4, NEW, known×4, NEW, known×4, ...]
"""
import random

from engine.leitner import get_cards_due, get_new_cards, get_known_cards


def build_session_queue(leitner_data, facts, groups, active_group_ids, settings):
    """
    Build ordered list of fact_ids for the session.

    Incremental Rehearsal logic:
      1. Pick up to new_cards_per_session "new" cards (box 0 or overdue box 1).
      2. Pick up to 8× known cards (box 3–5, stalest first).
      3. Interleave: [known×4, new, known×4, new, …, trailing knowns]
      4. Append remaining due cards (box 2+) at the end.
    """
    new_cards_limit = settings.get("new_cards_per_session", 2)

    # 1. Candidate new cards: box 0 (never practiced) from active groups
    new_candidates = get_new_cards(leitner_data, active_group_ids, groups)

    # Also treat box-1 overdue cards as "new" (need reinforcement)
    due_box1 = [
        fid
        for fid in get_cards_due(leitner_data)
        if leitner_data[fid]["box"] == 1 and fid not in new_candidates
    ]

    new_cards = (new_candidates + due_box1)[:new_cards_limit]

    # 2. Known cards pool (box 3–5), shuffle for variety
    known_pool = get_known_cards(leitner_data)
    random.shuffle(known_pool)

    # 3. Due box-2 cards
    due_box2 = [
        fid
        for fid in get_cards_due(leitner_data)
        if leitner_data[fid]["box"] == 2
    ]

    queue = []
    added = set()

    if not new_cards:
        # No new cards: just serve due cards + known review
        for fid in due_box2 + due_box1:
            if fid not in added:
                queue.append(fid)
                added.add(fid)
        if not queue:
            # Nothing due: review known cards anyway (up to 10)
            for fid in known_pool[:10]:
                if fid not in added:
                    queue.append(fid)
                    added.add(fid)
        return queue

    # 4. Build Incremental Rehearsal pattern
    ki = 0  # index into known_pool

    def pick_known(n):
        nonlocal ki
        picked = []
        while len(picked) < n and ki < len(known_pool):
            fid = known_pool[ki]
            ki += 1
            if fid not in added:
                picked.append(fid)
                added.add(fid)
        return picked

    for new_card in new_cards:
        # 4 known before each new card
        for fid in pick_known(4):
            queue.append(fid)
        if new_card not in added:
            queue.append(new_card)
            added.add(new_card)

    # Trailing known cards (up to 4)
    for fid in pick_known(4):
        queue.append(fid)

    # Append remaining due cards
    for fid in due_box2:
        if fid not in added:
            queue.append(fid)
            added.add(fid)

    return queue


def generate_distractors(fact_id, facts):
    """
    Generate exactly 3 wrong answer choices for tile mode.

    Rules (spec):
      - R + 6
      - R - 6 (if > 0)
      - result of a neighboring fact (same a, b±1)
    Falls back to R ± 12 when needed to reach 3 unique distractors.
    """
    fact = facts[fact_id]
    result = fact["result"]
    a, b = fact["a"], fact["b"]

    candidates = []

    # Neighbor fact distractor
    for delta in (1, -1):
        nb = b + delta
        if 2 <= nb <= 9:
            neighbor_result = a * nb
            if neighbor_result != result:
                candidates.append(neighbor_result)
                break

    # R ± 6
    if result + 6 <= 81:
        candidates.append(result + 6)
    if result - 6 >= 4:
        candidates.append(result - 6)

    # Fallbacks: R ± 12
    if result + 12 <= 81:
        candidates.append(result + 12)
    if result - 12 >= 4:
        candidates.append(result - 12)

    # De-duplicate and exclude correct answer
    seen = set()
    distractors = []
    for c in candidates:
        if c != result and c not in seen:
            seen.add(c)
            distractors.append(c)
        if len(distractors) == 3:
            break

    # Last-resort fallback
    fallback = 4
    while len(distractors) < 3:
        if fallback != result and fallback not in seen:
            distractors.append(fallback)
            seen.add(fallback)
        fallback += 4

    return distractors[:3]
