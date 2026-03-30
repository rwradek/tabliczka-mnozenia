"""
64 multiplication facts divided into 16 groups.
fact_id format: "axb" e.g. "6x7"
Range: ×2 to ×9 (×1 and ×10 excluded as trivial).
"""

# Introduction order: A-groups first (originals before inverses), then B, C, D
INTRODUCTION_ORDER = [
    "A1", "A3", "A2", "A4",
    "B1", "B3", "B2", "B4",
    "C1", "C3", "C2", "C4",
    "D1", "D3", "D2", "D4",
]

# Paired groups: each group's inverse partner
GROUP_PAIRS = {
    "A1": "A2", "A2": "A1",
    "A3": "A4", "A4": "A3",
    "B1": "B2", "B2": "B1",
    "B3": "B4", "B4": "B3",
    "C1": "C2", "C2": "C1",
    "C3": "C4", "C4": "C3",
    "D1": "D2", "D2": "D1",
    "D3": "D4", "D4": "D3",
}

# Which group in each pair is introduced first (the "original")
# Inverse groups require their pair to reach box ≥ 3 before introduction
INVERSE_GROUPS = {"A2", "A4", "B2", "B4", "C2", "C4", "D2", "D4"}

# Groups: each group contains exactly 4 fact_ids
# Note: 5x8 appears in both B3 and D3, 8x5 in both B4 and D4 (spec includes both)
GROUPS = {
    "A1": ["2x3", "3x4", "5x6", "7x8"],
    "A2": ["3x2", "4x3", "6x5", "8x7"],
    "A3": ["2x4", "3x6", "5x7", "9x9"],
    "A4": ["4x2", "6x3", "7x5", "8x8"],
    "B1": ["2x6", "3x7", "4x8", "9x5"],
    "B2": ["6x2", "7x3", "8x4", "5x9"],
    "B3": ["2x7", "4x6", "5x8", "6x6"],
    "B4": ["7x2", "6x4", "8x5", "7x7"],
    "C1": ["2x8", "3x9", "6x7", "5x5"],
    "C2": ["8x2", "9x3", "7x6", "4x4"],
    "C3": ["2x9", "4x7", "6x8", "3x3"],
    "C4": ["9x2", "7x4", "8x6", "2x2"],
    "D1": ["3x8", "4x9", "6x9", "7x9"],
    "D2": ["8x3", "9x4", "9x6", "9x7"],
    "D3": ["3x5", "4x5", "5x8", "8x9"],
    "D4": ["5x3", "5x4", "8x5", "9x8"],
}


def _build_facts():
    """Derive unique FACTS dict from group definitions."""
    facts = {}
    for group_facts in GROUPS.values():
        for fid in group_facts:
            if fid not in facts:
                a, b = map(int, fid.split("x"))
                facts[fid] = {"a": a, "b": b, "result": a * b}
    return facts


FACTS = _build_facts()


def get_fact_group(fact_id):
    """Return the primary group a fact belongs to (first in INTRODUCTION_ORDER)."""
    for group_id in INTRODUCTION_ORDER:
        if fact_id in GROUPS[group_id]:
            return group_id
    return None


def init_leitner_data(active_groups=None):
    """
    Initialize Leitner card data for all facts.
    active_groups: list of group IDs to mark as active (default: ['A1']).
    """
    if active_groups is None:
        active_groups = ["A1"]

    leitner = {}
    for fact_id in FACTS:
        leitner[fact_id] = {
            "box": 0,
            "next_review": None,
            "active": False,
            "history": [],
        }

    for group_id in active_groups:
        for fact_id in GROUPS.get(group_id, []):
            if fact_id in leitner:
                leitner[fact_id]["active"] = True

    return leitner
