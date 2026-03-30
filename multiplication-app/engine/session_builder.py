"""
Kard selection algorithm — two phases.

Phase 1 — Group learning (faza grup):
  Cards are served group-by-group following INTRODUCTION_ORDER.
  A group repeats until 2 consecutive error-free sessions, then the
  next group is unlocked.  Leitner boxes are updated but do NOT
  influence which cards are shown.

Phase 2 — Leitner rotation (faza Leitner):
  4 cards are picked from a Leitner-box copy following the frequency
  schedule [1,2,1,3,1,2,1,4,1,2,1,5]  (box 1 = 50%, box 2 = 25%,
  boxes 3–5 ≈ 8 % each).
  A batch of 4 repeats until 2 consecutive error-free sessions, then
  the next position in the schedule is used.

Logging:
  Every queue build and every phase transition is printed to stdout.
"""

import logging
import random

from data.facts import RAW_GROUPS, INTRODUCTION_ORDER

logger = logging.getLogger(__name__)

BATCH_SIZE = 4

# Phase-2 box frequency schedule.
# Position in list determines which box is chosen each turn.
# Box 1 every other slot; among the X-slots box 2 is most frequent.
BOX_SEQUENCE: list[int] = [1, 2, 1, 3, 1, 2, 1, 4, 1, 2, 1, 5]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_session_queue(leitner_data: dict, scheduler: dict) -> list[str]:
    """
    Return the ordered list of fact_ids for the next session.
    May mutate scheduler["current_batch"] (Phase 2 only).
    """
    phase = scheduler.get("phase", "groups")

    # Guard: if all groups done but phase not yet flipped
    if phase == "groups" and scheduler.get("current_group_idx", 0) >= len(INTRODUCTION_ORDER):
        scheduler["phase"] = "leitner"
        _init_leitner_phase(leitner_data, scheduler)
        phase = "leitner"

    if phase == "groups":
        return _build_groups_queue(scheduler)
    else:
        return _build_leitner_queue(leitner_data, scheduler)


def on_session_finished(scheduler: dict, leitner_data: dict, all_correct: bool) -> None:
    """
    Call after every session ends.
    Updates consecutive_clean counter and, when ≥ 2, advances the
    scheduler (next group / next box-sequence position).
    """
    phase = scheduler.get("phase", "groups")

    if phase == "groups":
        _finish_groups_session(scheduler, leitner_data, all_correct)
    else:
        _finish_leitner_session(scheduler, all_correct)


# ---------------------------------------------------------------------------
# Phase 1 helpers
# ---------------------------------------------------------------------------

def _build_groups_queue(scheduler: dict) -> list[str]:
    idx = scheduler.get("current_group_idx", 0)
    group_name = INTRODUCTION_ORDER[idx]
    cards = [f"{a}x{b}" for a, b in RAW_GROUPS[group_name]]
    random.shuffle(cards)
    clean = scheduler.get("consecutive_clean", 0)

    remaining_groups = INTRODUCTION_ORDER[idx + 1:]
    logger.info(
        "[Faza 1] Grupa: %s  |  Czyste z rzędu: %d/2  |  Pozostałe grupy: %s",
        group_name, clean, remaining_groups or "(brak — to ostatnia)",
    )
    logger.info("[Faza 1] Karty sesji: %s", cards)
    return cards


def _finish_groups_session(scheduler: dict, leitner_data: dict, all_correct: bool) -> None:
    idx = scheduler.get("current_group_idx", 0)
    group_name = INTRODUCTION_ORDER[idx] if idx < len(INTRODUCTION_ORDER) else "?"

    if all_correct:
        scheduler["consecutive_clean"] = scheduler.get("consecutive_clean", 0) + 1
    else:
        scheduler["consecutive_clean"] = 0

    clean = scheduler["consecutive_clean"]
    status = "✓ czysta" if all_correct else "✗ błędy"
    logger.info(
        "[Faza 1] Sesja %s  |  Czyste z rzędu: %d/2  |  Grupa: %s",
        status, clean, group_name,
    )

    if clean >= 2:
        new_idx = idx + 1
        scheduler["current_group_idx"] = new_idx
        scheduler["consecutive_clean"] = 0
        if new_idx < len(INTRODUCTION_ORDER):
            logger.info(
                "[Faza 1] Grupa %s opanowana! Następna: %s",
                group_name, INTRODUCTION_ORDER[new_idx],
            )
        else:
            logger.info(
                "[Faza 1] Wszystkie grupy opanowane! Przechodzę do Fazy 2 (Leitner)."
            )
            scheduler["phase"] = "leitner"
            _init_leitner_phase(leitner_data, scheduler)


# ---------------------------------------------------------------------------
# Phase 2 helpers
# ---------------------------------------------------------------------------

def _init_leitner_phase(leitner_data: dict, scheduler: dict) -> None:
    """Initialise box copies when entering / resetting Phase 2."""
    scheduler["box_seq_idx"] = 0
    scheduler["consecutive_clean"] = 0
    scheduler["current_batch"] = None
    copies: dict[str, list] = {}
    for b in range(1, 6):
        cards = [fid for fid, c in leitner_data.items() if c["box"] == b]
        random.shuffle(cards)
        copies[str(b)] = cards
    scheduler["box_copies"] = copies
    logger.info(
        "[Faza 2] Inicjalizacja kopii pudełek: %s",
        {k: len(v) for k, v in copies.items()},
    )


def _build_leitner_queue(leitner_data: dict, scheduler: dict) -> list[str]:
    # Repeat same batch while consecutive_clean < 2
    current_batch = scheduler.get("current_batch")
    if current_batch:
        shuffled = list(current_batch)
        random.shuffle(shuffled)
        logger.info("[Faza 2] Powtarzam partię (nie osiągnięto 2 czystych): %s", shuffled)
        return shuffled

    batch = _pick_new_batch(leitner_data, scheduler)
    scheduler["current_batch"] = batch
    return batch


def _pick_new_batch(leitner_data: dict, scheduler: dict) -> list[str]:
    """Draw BATCH_SIZE cards from the box indicated by the current sequence position."""
    box_seq_idx = scheduler.get("box_seq_idx", 0)
    target_box = BOX_SEQUENCE[box_seq_idx % len(BOX_SEQUENCE)]
    copies = scheduler.setdefault("box_copies", {str(b): [] for b in range(1, 6)})

    # Find a non-empty copy starting from target_box, then highest-priority fallback
    chosen_box = None
    # Priority: target first, then 1,2,3,4,5
    for candidate in [target_box] + [b for b in range(1, 6) if b != target_box]:
        _refill_if_empty(copies, candidate, leitner_data)
        if copies.get(str(candidate)):
            chosen_box = candidate
            break

    if chosen_box is None:
        logger.warning("[Faza 2] Brak kart we wszystkich pudełkach!")
        return []

    copy = copies[str(chosen_box)]
    batch = copy[:BATCH_SIZE]
    copies[str(chosen_box)] = copy[BATCH_SIZE:]
    remaining = len(copies[str(chosen_box)])

    logger.info(
        "[Faza 2] Pudełko: %d  |  Pozycja sekwencji: %d/%d  |  Karty: %s  |  Pozostało w kopii: %d",
        chosen_box,
        box_seq_idx % len(BOX_SEQUENCE) + 1,
        len(BOX_SEQUENCE),
        batch,
        remaining,
    )
    return batch


def _refill_if_empty(copies: dict, box_num: int, leitner_data: dict) -> None:
    """If the copy for box_num is empty, refill it from current live leitner data."""
    key = str(box_num)
    if not copies.get(key):
        cards = [fid for fid, c in leitner_data.items() if c["box"] == box_num]
        random.shuffle(cards)
        copies[key] = cards
        if cards:
            logger.info("[Faza 2] Uzupełniono kopię pudełka %d: %d kart.", box_num, len(cards))


def _finish_leitner_session(scheduler: dict, all_correct: bool) -> None:
    if all_correct:
        scheduler["consecutive_clean"] = scheduler.get("consecutive_clean", 0) + 1
    else:
        scheduler["consecutive_clean"] = 0

    clean = scheduler["consecutive_clean"]
    status = "✓ czysta" if all_correct else "✗ błędy"
    logger.info("[Faza 2] Sesja %s  |  Czyste z rzędu: %d/2", status, clean)

    if clean >= 2:
        old_idx = scheduler.get("box_seq_idx", 0)
        new_idx = (old_idx + 1) % len(BOX_SEQUENCE)
        scheduler["box_seq_idx"] = new_idx
        scheduler["consecutive_clean"] = 0
        scheduler["current_batch"] = None
        logger.info(
            "[Faza 2] Partia opanowana! Sekwencja: pozycja %d → pudełko %d",
            new_idx + 1,
            BOX_SEQUENCE[new_idx],
        )


# ---------------------------------------------------------------------------
# Distractor generation (tile mode) — unchanged
# ---------------------------------------------------------------------------

def generate_distractors(fact_id: str, facts: dict) -> list[int]:
    """
    Return 3 wrong answer options for tile mode.
    Rules: R±6, neighbour fact result.  Falls back to R±12.
    """
    fact = facts[fact_id]
    result = fact["result"]
    a, b = fact["a"], fact["b"]

    candidates: list[int] = []

    # Neighbour fact (same a, b±1)
    for delta in (1, -1):
        nb = b + delta
        if 2 <= nb <= 9:
            nr = a * nb
            if nr != result:
                candidates.append(nr)
                break

    if result + 6 <= 81:
        candidates.append(result + 6)
    if result - 6 >= 4:
        candidates.append(result - 6)
    if result + 12 <= 81:
        candidates.append(result + 12)
    if result - 12 >= 4:
        candidates.append(result - 12)

    seen: set[int] = set()
    distractors: list[int] = []
    for c in candidates:
        if c != result and c not in seen:
            seen.add(c)
            distractors.append(c)
        if len(distractors) == 3:
            break

    fallback = 4
    while len(distractors) < 3:
        if fallback != result and fallback not in seen:
            distractors.append(fallback)
            seen.add(fallback)
        fallback += 4

    return distractors[:3]
