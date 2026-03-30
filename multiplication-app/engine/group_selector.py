"""
Algorithm for suggesting the next group to introduce or revisit.

Priority order (spec):
  1. Regression — cards fell back to box 1 from box ≥ 3
  2. New group ready — all active groups reached box ≥ 3
  3. Stagnation — > 5 days with no session progress
"""
from datetime import date

from data.facts import GROUPS, INTRODUCTION_ORDER, GROUP_PAIRS, INVERSE_GROUPS
from engine.leitner import group_all_in_box_min
from engine.anti_interference import filter_candidate_groups


def suggest_next_group(state):
    """
    Analyse state and return a suggestion dict or None.

    Returns: {'group': str, 'reason': str} or None
    """
    leitner = state["leitner"]
    groups_status = state["groups"]

    active_groups = [
        g for g, info in groups_status.items() if info["status"] == "active"
    ]

    # 1. Regression check
    regressed = _find_regressed_group(leitner, active_groups)
    if regressed:
        return {"group": regressed, "reason": "regression"}

    # 2. Ready for new group?
    all_active_ready = active_groups and all(
        group_all_in_box_min(leitner, GROUPS[g], 3) for g in active_groups
    )

    if all_active_ready or not active_groups:
        next_group = _pick_next_group(groups_status, active_groups, leitner)
        if next_group:
            return {"group": next_group, "reason": "ready"}

    # 3. Stagnation
    stagnant = _find_stagnant_group(active_groups, state.get("stats", {}))
    if stagnant:
        return {"group": stagnant, "reason": "stagnation"}

    return None


def _find_regressed_group(leitner, active_groups):
    """Return a group ID if any of its cards recently dropped to box 1 from box ≥ 3."""
    today = date.today().isoformat()
    for group_id in active_groups:
        for fid in GROUPS[group_id]:
            card = leitner.get(fid, {})
            history = card.get("history", [])
            if card.get("box") == 1 and len(history) >= 2:
                # Last answer was wrong today, and the card was previously high
                last = history[-1]
                if not last["correct"] and last["date"] == today:
                    # Check if the card was at box ≥ 3 two history entries ago
                    prior_boxes = [
                        _infer_box_at(history, i)
                        for i in range(max(0, len(history) - 5), len(history) - 1)
                    ]
                    if any(b >= 3 for b in prior_boxes):
                        return group_id
    return None


def _infer_box_at(history, idx):
    """Roughly infer box number by counting net correct answers up to idx."""
    box = 0
    for h in history[: idx + 1]:
        if h["correct"]:
            box = min(box + 1, 5)
        else:
            box = 1
    return box


def _pick_next_group(groups_status, active_groups, leitner):
    """
    Find the next pending group to introduce, respecting prerequisites and
    anti-interference filtering.
    """
    active_set = set(active_groups)
    candidates = []

    for group_id in INTRODUCTION_ORDER:
        info = groups_status.get(group_id, {})
        if info.get("status") in ("active", "completed"):
            continue

        # Prerequisite: inverse groups wait for their pair to reach box ≥ 3
        if group_id in INVERSE_GROUPS:
            pair_id = GROUP_PAIRS.get(group_id)
            if pair_id:
                pair_info = groups_status.get(pair_id, {})
                # Pair must be active and at box ≥ 3
                if pair_info.get("status") != "active":
                    continue
                if not group_all_in_box_min(leitner, GROUPS[pair_id], 3):
                    continue

        candidates.append(group_id)
        break  # take the first viable candidate only

    if not candidates:
        return None

    # Anti-interference filter (falls back to unfiltered if all removed)
    filtered = filter_candidate_groups(candidates, active_groups)
    return filtered[0] if filtered else None


def _find_stagnant_group(active_groups, stats):
    """Return first active group if no session progress in 5+ days."""
    last_session = stats.get("last_session")
    if not last_session:
        return None
    today = date.today()
    days_since = (today - date.fromisoformat(last_session)).days
    if days_since >= 5 and active_groups:
        return active_groups[0]
    return None


def activate_group(state, group_id):
    """
    Mark a group as active and enable its facts in the Leitner system.
    Call this when the parent approves the suggested group.
    """
    leitner = state["leitner"]
    groups_status = state["groups"]

    for fid in GROUPS[group_id]:
        if fid in leitner:
            leitner[fid]["active"] = True

    groups_status[group_id] = {"status": "active"}
