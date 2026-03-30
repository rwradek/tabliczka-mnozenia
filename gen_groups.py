"""
Generuje 64 karty w 16 grupach zgodnie ze specyfikacją SPEC.md
i zapisuje wynik do facts_groups.json oraz facts_groups_readable.txt

Zasady grupowania:
- Zakres: ×2 do ×9 (bez ×1 i ×10)
- Kwadraty (n×n): 8 kart, tylko jedna wersja
- Pary (a×b, a≠b): obie kolejności jako osobne karty
- Łącznie: 64 karty w 16 grupach po 4 karty
- Grupy "parzyste" (A2, A4...) zawierają odwrotności grup "nieparzystych"
- Odwrotności nigdy w tej samej grupie
- Brak wspólnych cyfr w grupie (gdzie możliwe)
- Wyniki możliwie odległe (min. ~10)
- Kwadraty jako "kotwice" — jeden na grupę (w grupach C i D)
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Definicja karty
# ---------------------------------------------------------------------------

@dataclass
class Card:
    id: str          # np. "2x3"
    a: int
    b: int
    result: int
    group: str       # np. "A1"
    is_square: bool
    pair_id: Optional[str]  # id odwrotności, np. "3x2"; None dla kwadratów

    def __repr__(self):
        pair = f" [para: {self.pair_id}]" if self.pair_id else " [kwadrat]"
        return f"{self.id}={self.result} (grupa {self.group}){pair}"


# ---------------------------------------------------------------------------
# Definicja grup — zakodowana ręcznie zgodnie ze specyfikacją
# ---------------------------------------------------------------------------

# Format: (a, b)  →  karta a×b=a*b
# Grupy A/B: małe liczby, duże różnice wyników
# Grupy C: średnie, wprowadzenie 8 i 9
# Grupy D: najtrudniejsze fakty

RAW_GROUPS: dict[str, list[tuple[int, int]]] = {
    # --- Faza 1: małe liczby ---
    "A1": [(2, 3), (3, 4), (5, 6), (7, 8)],           # wyniki: 6, 12, 30, 56
    "A2": [(3, 2), (4, 3), (6, 5), (8, 7)],           # odwrotności A1
    "A3": [(2, 4), (3, 6), (5, 7), (9, 9)],           # wyniki: 8, 18, 35, 81
    "A4": [(4, 2), (6, 3), (7, 5), (8, 8)],           # odwrotności A3 + kwadrat

    # --- Faza 2: średnie, wprowadzenie ×8 i ×9 ---
    "B1": [(2, 6), (3, 7), (4, 8), (9, 5)],           # wyniki: 12, 21, 32, 45
    "B2": [(6, 2), (7, 3), (8, 4), (5, 9)],           # odwrotności B1
    "B3": [(2, 7), (4, 6), (5, 8), (6, 6)],           # wyniki: 14, 24, 40, 36
    "B4": [(7, 2), (6, 4), (8, 5), (7, 7)],           # odwrotności B3 + kwadraty

    # --- Faza 3: ×6, ×7, ×8, ×9 wzajemnie + kwadraty ---
    "C1": [(2, 8), (3, 9), (6, 7), (5, 5)],           # wyniki: 16, 27, 42, 25
    "C2": [(8, 2), (9, 3), (7, 6), (4, 4)],           # odwrotności C1 + kwadraty
    "C3": [(2, 9), (4, 7), (6, 8), (3, 3)],           # wyniki: 18, 28, 48, 9
    "C4": [(9, 2), (7, 4), (8, 6), (2, 2)],           # odwrotności C3 + kwadraty

    # --- Faza 4: najtrudniejsze fakty ---
    "D1": [(3, 8), (4, 9), (6, 9), (7, 9)],           # wyniki: 24, 36, 54, 63
    "D2": [(8, 3), (9, 4), (9, 6), (9, 7)],           # odwrotności D1
    "D3": [(3, 5), (4, 5), (2, 5), (8, 9)],           # wyniki: 15, 20, 10, 72
    "D4": [(5, 3), (5, 4), (5, 2), (9, 8)],           # odwrotności D3
}

# Mapowanie: która grupa jest odwrotnością której
PAIR_GROUPS: dict[str, str] = {
    "A1": "A2", "A2": "A1",
    "A3": "A4", "A4": "A3",
    "B1": "B2", "B2": "B1",
    "B3": "B4", "B4": "B3",
    "C1": "C2", "C2": "C1",
    "C3": "C4", "C4": "C3",
    "D1": "D2", "D2": "D1",
    "D3": "D4", "D4": "D3",
}

# Kolejność wprowadzania grup przez algorytm
INTRODUCTION_ORDER = [
    "A1", "A3", "A2", "A4",
    "B1", "B3", "B2", "B4",
    "C1", "C3", "C2", "C4",
    "D1", "D3", "D2", "D4",
]


# ---------------------------------------------------------------------------
# Budowanie kart
# ---------------------------------------------------------------------------

def build_cards() -> list[Card]:
    all_cards: list[Card] = []

    for group_id, pairs in RAW_GROUPS.items():
        for (a, b) in pairs:
            is_sq = (a == b)
            card_id = f"{a}x{b}"
            pair_id = f"{b}x{a}" if not is_sq else None
            card = Card(
                id=card_id,
                a=a,
                b=b,
                result=a * b,
                group=group_id,
                is_square=is_sq,
                pair_id=pair_id,
            )
            all_cards.append(card)

    return all_cards


# ---------------------------------------------------------------------------
# Walidacja
# ---------------------------------------------------------------------------

def validate(cards: list[Card]) -> list[str]:
    errors: list[str] = []
    ids = [c.id for c in cards]

    # 1. Dokładnie 64 karty
    if len(cards) != 64:
        errors.append(f"Oczekiwano 64 kart, znaleziono {len(cards)}")

    # 2. Brak duplikatów id
    if len(ids) != len(set(ids)):
        dupes = [x for x in ids if ids.count(x) > 1]
        errors.append(f"Duplikaty kart: {set(dupes)}")

    # 3. Każda grupa ma dokładnie 4 karty
    from collections import Counter
    group_counts = Counter(c.group for c in cards)
    for g, count in group_counts.items():
        if count != 4:
            errors.append(f"Grupa {g}: oczekiwano 4 kart, jest {count}")

    # 4. Odwrotności nie są w tej samej grupie
    card_map = {c.id: c for c in cards}
    for card in cards:
        if card.pair_id and card.pair_id in card_map:
            pair = card_map[card.pair_id]
            if pair.group == card.group:
                errors.append(
                    f"Odwrotności {card.id} i {pair.id} są w tej samej grupie {card.group}"
                )

    # 5. Poprawność wyników
    for card in cards:
        if card.result != card.a * card.b:
            errors.append(f"Błędny wynik: {card.id}={card.result}, powinno być {card.a * card.b}")

    # 6. Zakres ×2–×9
    for card in cards:
        if not (2 <= card.a <= 9 and 2 <= card.b <= 9):
            errors.append(f"Karta poza zakresem ×2–×9: {card.id}")

    # 7. Parowanie grup — odwrotności w oczekiwanej grupie
    for card in cards:
        if card.pair_id and card.pair_id in card_map:
            pair = card_map[card.pair_id]
            expected_pair_group = PAIR_GROUPS.get(card.group)
            if expected_pair_group and pair.group != expected_pair_group:
                errors.append(
                    f"Odwrotność {card.pair_id} powinna być w grupie "
                    f"{expected_pair_group}, jest w {pair.group}"
                )

    return errors


# ---------------------------------------------------------------------------
# Zapis do JSON
# ---------------------------------------------------------------------------

def save_json(cards: list[Card], path: str = "facts_groups.json") -> None:
    # Struktura: {group_id: [card_dict, ...]}
    groups: dict[str, list] = {g: [] for g in RAW_GROUPS}
    for card in cards:
        groups[card.group].append(asdict(card))

    output = {
        "meta": {
            "total_cards": len(cards),
            "total_groups": len(groups),
            "introduction_order": INTRODUCTION_ORDER,
            "pair_groups": PAIR_GROUPS,
            "description": (
                "64 karty, 16 grup po 4. Grupy parzyste zawierają odwrotności "
                "grup nieparzystych. Kwadraty tylko jedna wersja."
            ),
        },
        "groups": groups,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ Zapisano JSON → {path}")


# ---------------------------------------------------------------------------
# Zapis do pliku czytelnego dla człowieka
# ---------------------------------------------------------------------------

def save_readable(cards: list[Card], path: str = "facts_groups_readable.txt") -> None:
    from collections import Counter
    group_counts = Counter(c.group for c in cards)

    lines = []
    lines.append("=" * 60)
    lines.append("GRUPY FAKTÓW — 64 karty, 16 grup")
    lines.append("=" * 60)

    phases = [
        ("Faza 1 — Małe liczby", ["A1", "A2", "A3", "A4"]),
        ("Faza 2 — Średnie, wprowadzenie ×8 i ×9", ["B1", "B2", "B3", "B4"]),
        ("Faza 3 — ×6,×7,×8,×9 wzajemnie + kwadraty", ["C1", "C2", "C3", "C4"]),
        ("Faza 4 — Najtrudniejsze fakty", ["D1", "D2", "D3", "D4"]),
    ]

    card_map = {c.id: c for c in cards}

    for phase_name, group_ids in phases:
        lines.append(f"\n{'─' * 60}")
        lines.append(f"  {phase_name}")
        lines.append(f"{'─' * 60}")

        for gid in group_ids:
            g_cards = [c for c in cards if c.group == gid]
            pair_gid = PAIR_GROUPS.get(gid, "—")
            header = f"Grupa {gid}  (para z: {pair_gid})"
            lines.append(f"\n  {header}")

            for card in g_cards:
                sq_mark = " [kwadrat]" if card.is_square else ""
                pair_mark = f" ← odwrotność {card.pair_id}" if card.pair_id else ""
                lines.append(f"    {card.a} × {card.b} = {card.result}{sq_mark}{pair_mark}")

    lines.append(f"\n{'=' * 60}")
    lines.append(f"Łącznie: {len(cards)} kart w {len(RAW_GROUPS)} grupach")
    lines.append("\nKolejność wprowadzania grup przez algorytm:")
    for i, gid in enumerate(INTRODUCTION_ORDER, 1):
        lines.append(f"  {i:2}. {gid}")
    lines.append("=" * 60)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✓ Zapisano czytelny raport → {path}")


# ---------------------------------------------------------------------------
# Zapis siatki 10×10
# ---------------------------------------------------------------------------

def save_grid(cards: list[Card], path: str = "facts_groups_grid.txt") -> None:
    # Buduj słownik (a, b) → group_id
    card_map: dict[tuple[int, int], str] = {
        (c.a, c.b): c.group for c in cards
    }

    # Szerokość komórki: "6×7=42 (A1)" → najdłuższy możliwy wpis to 13 znaków
    # Ujednolicamy do stałej szerokości
    CELL = 14  # szerokość kolumny

    lines = []
    lines.append("=" * (CELL * 11 + 2))
    lines.append("TABLICA 10×10 — wyniki i przypisane grupy")
    lines.append("Komórki: a×b=wynik (grupa)  |  '-' = poza zakresem lub trywialne")
    lines.append("=" * (CELL * 11 + 2))

    # Nagłówek kolumn
    header = f"{'':>{CELL}}" + "".join(f"{'×' + str(b):>{CELL}}" for b in range(1, 11))
    lines.append(header)
    lines.append("─" * (CELL * 11 + 2))

    for a in range(1, 11):
        row_parts = [f"{str(a) + '×':>{CELL}}"]
        for b in range(1, 11):
            result = a * b
            group = card_map.get((a, b))
            if group:
                cell = f"{a}×{b}={result}({group})"
            else:
                cell = "-"
            row_parts.append(f"{cell:>{CELL}}")
        lines.append("".join(row_parts))

    lines.append("─" * (CELL * 11 + 2))

    # Legenda faz
    lines.append("\nLegenda grup:")
    phase_info = [
        ("A1–A4", "Faza 1 — małe liczby (×2–×7)"),
        ("B1–B4", "Faza 2 — średnie, wprowadzenie ×8 i ×9"),
        ("C1–C4", "Faza 3 — ×6,×7,×8,×9 wzajemnie + kwadraty"),
        ("D1–D4", "Faza 4 — najtrudniejsze fakty"),
    ]
    for groups, desc in phase_info:
        lines.append(f"  {groups:10} {desc}")

    lines.append(f"\n'-' oznacza: ×1, ×10 (pominięte jako trywialne) lub n×n już ujęty jako kwadrat")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✓ Zapisano siatkę 10×10 → {path}")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def main():
    print("Generowanie grup faktów...")

    cards = build_cards()
    print(f"  Zbudowano {len(cards)} kart")

    errors = validate(cards)
    if errors:
        print("\n⚠️  Błędy walidacji:")
        for e in errors:
            print(f"  • {e}")
        return

    print("  Walidacja: OK")

    save_json(cards)
    save_readable(cards)
    save_grid(cards)

    # Podgląd w konsoli
    print("\nPodgląd grup:")
    for gid in INTRODUCTION_ORDER:
        g_cards = [c for c in cards if c.group == gid]
        items = ", ".join(f"{c.a}×{c.b}={c.result}" for c in g_cards)
        print(f"  {gid}: {items}")


if __name__ == "__main__":
    main()