"""
Multiplication fact definitions — 16 groups of 4 cards each.
fact_id format: "axb"  e.g. "6x7"
Range: ×2 to ×9.
"""

# ---------------------------------------------------------------------------
# RAW_GROUPS — canonical definition (tuples of (a, b))
# ---------------------------------------------------------------------------
RAW_GROUPS: dict[str, list[tuple[int, int]]] = {
    # Faza 1: małe liczby
    "A1": [(2, 3), (3, 4), (5, 6), (7, 8)],          # wyniki: 6, 12, 30, 56
    "A2": [(3, 2), (4, 3), (6, 5), (8, 7)],          # odwrotności A1
    "A3": [(2, 4), (3, 6), (5, 7), (9, 9)],          # wyniki: 8, 18, 35, 81
    "A4": [(4, 2), (6, 3), (7, 5), (8, 8)],          # odwrotności A3 + kwadrat
    # Faza 2: średnie, wprowadzenie ×8 i ×9
    "B1": [(2, 6), (3, 7), (4, 8), (9, 5)],          # wyniki: 12, 21, 32, 45
    "B2": [(6, 2), (7, 3), (8, 4), (5, 9)],          # odwrotności B1
    "B3": [(2, 7), (4, 6), (5, 8), (6, 6)],          # wyniki: 14, 24, 40, 36
    "B4": [(7, 2), (6, 4), (8, 5), (7, 7)],          # odwrotności B3 + kwadraty
    # Faza 3: ×6, ×7, ×8, ×9 wzajemnie + kwadraty
    "C1": [(2, 8), (3, 9), (6, 7), (5, 5)],          # wyniki: 16, 27, 42, 25
    "C2": [(8, 2), (9, 3), (7, 6), (4, 4)],          # odwrotności C1 + kwadraty
    "C3": [(2, 9), (4, 7), (6, 8), (3, 3)],          # wyniki: 18, 28, 48, 9
    "C4": [(9, 2), (7, 4), (8, 6), (2, 2)],          # odwrotności C3 + kwadraty
    # Faza 4: najtrudniejsze fakty
    "D1": [(3, 8), (4, 9), (6, 9), (7, 9)],          # wyniki: 24, 36, 54, 63
    "D2": [(8, 3), (9, 4), (9, 6), (9, 7)],          # odwrotności D1
    "D3": [(3, 5), (4, 5), (2, 5), (8, 9)],          # wyniki: 15, 20, 10, 72
    "D4": [(5, 3), (5, 4), (5, 2), (9, 8)],          # odwrotności D3
}

# Kolejność wprowadzania grup
INTRODUCTION_ORDER: list[str] = [
    "A1", "A3", "A2", "A4",
    "B1", "B3", "B2", "B4",
    "C1", "C3", "C2", "C4",
    "D1", "D3", "D2", "D4",
]

# Derived: group → list of fact_ids
GROUPS: dict[str, list[str]] = {
    g: [f"{a}x{b}" for a, b in pairs]
    for g, pairs in RAW_GROUPS.items()
}


def _build_facts() -> dict:
    facts: dict = {}
    for group_facts in GROUPS.values():
        for fid in group_facts:
            if fid not in facts:
                a, b = map(int, fid.split("x"))
                facts[fid] = {"a": a, "b": b, "result": a * b}
    return facts


FACTS: dict = _build_facts()


def init_leitner_data() -> dict:
    """Return initial Leitner state for all facts (all in box 0)."""
    return {fid: {"box": 0, "history": []} for fid in FACTS}
