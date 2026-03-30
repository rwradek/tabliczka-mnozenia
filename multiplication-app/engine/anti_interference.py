"""
Anti-interference filter: prevents introducing groups that share too many
digits or have results too close together with currently active groups.
"""
from data.facts import GROUPS, FACTS


def groups_interfere(group1_id, group2_id):
    """
    Return True if two groups would cause associative interference.

    Criteria:
      - They share 3+ operand digits, OR
      - They have 3+ result pairs within 6 of each other
    """
    g1_facts = [FACTS[fid] for fid in GROUPS.get(group1_id, []) if fid in FACTS]
    g2_facts = [FACTS[fid] for fid in GROUPS.get(group2_id, []) if fid in FACTS]

    # Shared operand digits
    g1_digits = {f["a"] for f in g1_facts} | {f["b"] for f in g1_facts}
    g2_digits = {f["a"] for f in g2_facts} | {f["b"] for f in g2_facts}

    if len(g1_digits & g2_digits) >= 3:
        return True

    # Close results
    g1_results = [f["result"] for f in g1_facts]
    g2_results = [f["result"] for f in g2_facts]

    close_pairs = sum(
        1
        for r1 in g1_results
        for r2 in g2_results
        if r1 != r2 and abs(r1 - r2) <= 6
    )

    return close_pairs >= 3


def filter_candidate_groups(candidate_group_ids, active_group_ids):
    """
    Remove candidates that interfere with any active group.
    If ALL candidates are filtered out, return the original list (spec: prefer
    simplicity over perfect interference avoidance).
    """
    filtered = [
        g
        for g in candidate_group_ids
        if not any(groups_interfere(g, ag) for ag in active_group_ids)
    ]
    return filtered if filtered else candidate_group_ids
