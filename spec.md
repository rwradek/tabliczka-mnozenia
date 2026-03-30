# Specyfikacja implementacji — aplikacja do nauki tabliczki mnożenia

## Kontekst i cel

Aplikacja służy do nauki tabliczki mnożenia dla 8-letniego dziecka, które:
- myli podobne zestawy (np. 6×7 i 7×8) — problem interferencji asocjacyjnej
- szybko zapomina po nauce — wymaga powtórek rozłożonych w czasie
- uczy się wzrokowo — UI powinien być prosty, czytelny, z lekkimi animacjami
- pracuje samodzielnie na tablecie, rodzic nadzoruje przez osobny panel

Dziecko jest na **etapie automatyzacji** — potrafi już wyprowadzić wynik, celem jest szybkie i pewne przypominanie bez liczenia.

---

## Architektura systemu

```
[Tablet dziecka]   ──── HTTP (Wi-Fi) ────┐
                                         ├── [Serwer Python/Flask, port 5000]  ←→  [session_data.json]
[Komputer rodzica] ──── HTTP (Wi-Fi) ────┘
```

- Serwer uruchamiany lokalnie: `python server.py`
- Dziecko otwiera `http://192.168.x.x:5000/child/` na tablecie
- Rodzic otwiera `http://192.168.x.x:5000/parent/` na komputerze
- Dane zapisywane do `session_data.json` (brak zewnętrznej bazy danych)

---

## Struktura plików projektu

```
multiplication-app/
├── server.py                   # Flask, routing, zapis/odczyt JSON
├── engine/
│   ├── leitner.py              # logika 5 pudełek
│   ├── session_builder.py      # Incremental Rehearsal, kolejka pytań
│   ├── group_selector.py       # algorytm doboru grupy faktów
│   └── anti_interference.py    # filtr podobnych faktów w sesji
├── data/
│   ├── facts.py                # definicje 64 kart i 16 grup
│   └── session_data.json       # trwały stan (auto-generowany przy starcie)
├── templates/
│   ├── child.html              # UI dziecka
│   └── parent.html             # UI rodzica / statystyki
└── static/
    ├── child.css
    ├── child.js
    ├── parent.css
    └── parent.js
```

---

## Zbiór faktów — 64 karty, 16 grup

### Założenia

- Zakres: ×2 do ×9 (pominięto ×1 i ×10 jako trywialne)
- Kwadraty (2×2 ... 9×9): 8 kart, tylko jedna wersja (brak odwrotności)
- Pary (a×b gdzie a≠b): obie kolejności jako **osobne karty** (2×3 i 3×2 to dwie niezależne karty w Leitnerze)
- Łącznie: 8 kwadratów + 56 par = **64 karty**
- Grupy "A" zawierają oryginały, grupy "B" zawierają odwrotności — algorytm nie wprowadza grupy B dopóki fakty z powiązanej grupy A nie osiągną box ≥ 3

### Reguły grupowania

- Brak wspólnych cyfr w obrębie grupy (gdzie możliwe)
- Wyniki możliwie odległe (min. ~10 między wynikami w grupie)
- Kwadraty rozłożone jako "kotwice" — po jednym na grupę
- Pary odwrotne nigdy w tej samej grupie

### Tabela grup

| Grupa | Karta 1 | Karta 2 | Karta 3 | Karta 4 | Para z grupą |
|-------|---------|---------|---------|---------|--------------|
| **A1** | 2×3=6   | 3×4=12  | 5×6=30  | 7×8=56  | → A2 |
| **A2** | 3×2=6   | 4×3=12  | 6×5=30  | 8×7=56  | odwrotności A1 |
| **A3** | 2×4=8   | 3×6=18  | 5×7=35  | 9×9=81  | → A4 |
| **A4** | 4×2=8   | 6×3=18  | 7×5=35  | 8×8=64  | odwrotności A3 |
| **B1** | 2×6=12  | 3×7=21  | 4×8=32  | 9×5=45  | → B2 |
| **B2** | 6×2=12  | 7×3=21  | 8×4=32  | 5×9=45  | odwrotności B1 |
| **B3** | 2×7=14  | 4×6=24  | 5×8=40  | 6×6=36  | → B4 |
| **B4** | 7×2=14  | 6×4=24  | 8×5=40  | 7×7=49  | odwrotności B3 |
| **C1** | 2×8=16  | 3×9=27  | 6×7=42  | 5×5=25  | → C2 |
| **C2** | 8×2=16  | 9×3=27  | 7×6=42  | 4×4=16  | odwrotności C1 |
| **C3** | 2×9=18  | 4×7=28  | 6×8=48  | 3×3=9   | → C4 |
| **C4** | 9×2=18  | 7×4=28  | 8×6=48  | 2×2=4   | odwrotności C3 |
| **D1** | 3×8=24  | 4×9=36  | 6×9=54  | 7×9=63  | → D2 |
| **D2** | 8×3=24  | 9×4=36  | 9×6=54  | 9×7=63  | odwrotności D1 |
| **D3** | 3×5=15  | 4×5=20  | 5×8=40  | 8×9=72  | → D4 |
| **D4** | 5×3=15  | 5×4=20  | 8×5=40  | 9×8=72  | odwrotności D3 |

### Harmonogram wprowadzania grup (sugestia dla algorytmu)

```
Tydzień 1: A1 → A3
Tydzień 2: A2 → A4   (gdy A1, A3 osiągną box ≥ 3)
Tydzień 3: B1 → B3
Tydzień 4: B2 → B4
Tydzień 5: C1 → C3
Tydzień 6: C2 → C4
Tydzień 7: D1 → D3
Tydzień 8: D2 → D4
```

---

## Moduł `engine/leitner.py`

### System 5 pudełek

| Pudełko | Powtórka co | Opis |
|---------|-------------|------|
| 1 | 1 dzień | nowe i błędne |
| 2 | 2 dni | słabe |
| 3 | 4 dni | średnie |
| 4 | 8 dni | dobre |
| 5 | 16 dni | opanowane |

### Zasady ruchu kart

- Poprawna odpowiedź → przesuń do box+1 (max 5)
- Błędna odpowiedź → cofnij do box 1
- Karty 2×3 i 3×2 są **całkowicie niezależne** — błąd w jednej nie wpływa na drugą
- Kryterium opanowania: odpowiedź w < 3 sek. **i** box ≥ 4

---

## Moduł `engine/session_builder.py`

### Warunek końca sesji (podwójny)

```
Sesja kończy się gdy:
  (czas ≥ 12 min) AND (ukończono minimalne powtórki)

minimalne powtórki = suma dla kart zaplanowanych na dziś:
  box 1 → 3 powtórki
  box 2 → 2 powtórki
  box 3–5 → 1 powtórka

Twardy limit: 20 minut (ochrona przed przeciążeniem dziecka)
```

### Algorytm Incremental Rehearsal (proporcja 8:1)

```
Budowanie kolejki pytań:
1. Wybierz 1–2 karty do wprowadzenia:
   - box 0 (nigdy niećwiczone) z aktywnej grupy
   - LUB karty zaległe z box 1 (next_review ≤ dziś)
2. Wybierz 8 kart "znanych" (box 3–5, dawno nie powtarzane)
3. Kolejność w sesji:
   [znana × 4, NOWA, znana × 4, NOWA, znana]
   → ~80% odpowiedzi poprawnych → utrzymuje motywację
4. Po sesji: zaktualizuj next_review dla każdej karty
```

### Generowanie dystraktorów (tryb kafelków)

```
Dla poprawnej odpowiedzi R generuj 3 dystraktorów:
  - R + 6
  - R - 6  (jeśli > 0)
  - wynik sąsiedniego faktu (np. dla 6×7=42 → dystraktorem jest 6×8=48)
Jeśli wartości się pokrywają lub wychodzą poza zakres → zastąp R ± 12
```

---

## Moduł `engine/group_selector.py`

### Logika doboru kolejnej grupy (uruchamiana po każdej sesji)

```
1. Regresja (priorytet najwyższy):
   - Jeśli karty wróciły do box 1 z box ≥ 3
   → wybierz grupę z kartą o NAJWCZEŚNIEJSZEJ next_review
   → wstrzymaj wprowadzanie nowych grup

2. Gotowość do nowej grupy:
   - Wszystkie karty aktywnych grup osiągnęły box ≥ 3
   → zaproponuj kolejną grupę wg kolejności A1→A3→A2→A4→B1...

3. Filtr anti-interference:
   - Odrzuć grupy dzielące cyfry lub bliskie wyniki z aktualnie ćwiczonymi
   - Jeśli filtr odrzuca WSZYSTKIE kandydatki → pomiń filtr,
     wybierz kolejną wg kolejności (prostota > perfekcja)

4. Stagnacja:
   - Minęło > 5 dni bez postępu
   → zaproponuj powtórkę najstarszej aktywnej grupy
```

Rodzic widzi w panelu sugestię algorytmu i może ją nadpisać.

---

## Model sesji — wiele sesji dziennie

```
Sesja = slot przygotowany przez rodzica lub algorytm,
        czekający na uruchomienie przez dziecko.

Cykl:
  algorytm/rodzic → tworzy slot sesji (które karty, tryb odpowiedzi)
  dziecko → otwiera tablet, widzi "Zacznij sesję"
  po sesji → slot oznaczony jako ukończony, wyniki zapisane

Wiele sesji dziennie:
  - brak limitu liczby sesji na dzień
  - algorytm może zaproponować dodatkową sesję
    jeśli pierwsza wykazała dużo błędów (box 1 zapełniony)
  - dziecko widzi: "Sesja 1/2 dziś ukończona ✓ — sesja 2 czeka"
```

---

## Trwałość danych — `session_data.json`

### Momenty zapisu

```
1. Co 5 odpowiedzi (konfigurowalne) — ochrona przed awarią
2. Po zakończeniu każdej sesji — pełny zapis
3. Przy zamknięciu serwera (sygnał SIGTERM/SIGINT) — ostatni zapis

Przy starcie serwera:
  - plik istnieje → wczytaj stan i kontynuuj
  - plik nie istnieje → zainicjuj 64 karty (box=0, nieaktywne)
```

### Schemat JSON

```json
{
  "leitner": {
    "2x3": {
      "box": 2,
      "next_review": "2026-03-30",
      "active": true,
      "history": [
        {"date": "2026-03-28", "correct": true, "response_ms": 1840},
        {"date": "2026-03-29", "correct": false, "response_ms": 4200}
      ]
    },
    "3x2": {"box": 0, "next_review": null, "active": false, "history": []},
    "8x8": {"box": 5, "next_review": "2026-04-12", "active": true, "history": []}
  },
  "groups": {
    "A1": {"status": "completed"},
    "A2": {"status": "active"},
    "A3": {"status": "active"},
    "A4": {"status": "pending"}
  },
  "pending_sessions": [
    {"id": "s_20260329_eve", "created_by": "algorithm", "status": "pending"}
  ],
  "completed_sessions": [
    {
      "id": "s_20260329_mor",
      "completed_at": "2026-03-29T08:34:00",
      "answers": 18,
      "correct": 15,
      "avg_response_ms": 2100
    }
  ],
  "settings": {
    "answer_mode": "keyboard",
    "session_length_min": 12,
    "session_hard_limit_min": 20,
    "new_cards_per_session": 2,
    "autosave_every_n": 5,
    "mastery_threshold_ms": 3000
  },
  "stats": {
    "total_sessions": 14,
    "total_answers": 312,
    "last_session": "2026-03-29"
  }
}
```

---

## Serwer — `server.py` (Flask)

### Endpointy

**Widok dziecka `/child/`:**
```
GET  /child/                → strona nauki (child.html)
GET  /child/next            → JSON: następne pytanie z sesji
POST /child/answer          → JSON: {fact_id, answer, response_time_ms}
                              zwraca: {correct, correct_answer, box_moved_to}
GET  /child/session-status  → {questions_done, questions_total, time_elapsed_s}
```

**Widok rodzica `/parent/`:**
```
GET  /parent/               → panel statystyk (parent.html)
GET  /parent/stats          → JSON z danymi do wykresów
GET  /parent/settings       → aktualna konfiguracja
POST /parent/settings       → zmiana konfiguracji
POST /parent/override-group → ręczna zmiana sugerowanej grupy
```

**System:**
```
POST /system/save           → wymuszony zapis do JSON
```

---

## Frontend dziecka — `child.html`

### Tryb klawiatury

```
┌──────────────────────────────┐
│                              │
│         6  ×  7  =  ?        │   ← duże cyfry (min. 72px)
│                              │
│       [ _____ ]  ↵           │   ← pole tekstowe, autofocus
│                              │
│  ████████░░░░  sesja 8/15    │   ← pasek postępu
└──────────────────────────────┘
```

### Tryb kafelków (4 opcje)

```
┌──────────────────────────────┐
│         6  ×  7  =  ?        │
│                              │
│      ┌──────┐  ┌──────┐      │
│      │  42  │  │  48  │      │
│      └──────┘  └──────┘      │
│      ┌──────┐  ┌──────┐      │
│      │  35  │  │  56  │      │
│      └──────┘  └──────┘      │
└──────────────────────────────┘
Dystraktorzy dobierani wg algorytmu (R±6, sąsiedni fakt)
```

### Animacje

- ✅ Poprawna: zielony błysk + "pop" karty (CSS scale 1→1.1→1, 200ms)
- ❌ Błędna: czerwone drżenie (CSS shake, 300ms) + poprawna odpowiedź przez 2 sek.
- 🎉 Co 5 poprawnych z rzędu: confetti (0.5 sek., nie blokuje następnego pytania)
- Karta wchodzi z prawej (CSS slide-in, 150ms)

---

## Frontend rodzica — `parent.html`

### Zakładka 1: Siatka postępu (10×10, zakresy ×1–×10 widoczne, ×1 i ×10 szare)

```
Kolory pudełek:
  box 0 → szary (nieaktywne)
  box 1 → czerwony
  box 2 → pomarańczowy
  box 3 → żółty
  box 4 → jasnozielony
  box 5 → ciemnozielony
```

### Zakładka 2: Pudełka Leitnera

```
  Box 1  │  Box 2  │  Box 3  │  Box 4  │  Box 5
  ██████ │  ████   │  ███    │  ██     │  █
  12 kart│  8 kart │  5 kart │  4 karty│  2 karty
  (dziś) │ (jutro) │(za 3 dn)│(za 7 dn)│(za 14 dn)
```

### Zakładka 3: Historia sesji

- Tabela: data, liczba pytań, % poprawnych, średni czas odpowiedzi
- Wykres liniowy: % poprawnych na przestrzeni ostatnich 14 dni
- Top 5 najtrudniejszych faktów (najwięcej błędów)

### Zakładka 4: Konfiguracja

```
Tryb odpowiedzi:      ○ Klawiatura  ○ Kafelki
Długość sesji:        [12] minut
Nowe karty/sesja:     [2]
Autosave co:          [5] odpowiedzi
Próg opanowania:      [3000] ms
Sugestia algorytmu:   "Następna grupa: B1" [Zatwierdź] [Zmień]
```

---

## Kolejność implementacji

### Etap 1 — Fundament danych
- `data/facts.py` — 64 karty, 16 grup, reguły parowania
- `data/session_data.json` — inicjalizacja przy pierwszym starcie
- Funkcje zapis/odczyt JSON z obsługą SIGTERM

### Etap 2 — Silnik algorytmu
- `engine/leitner.py` — ruch kart, daty powtórek
- `engine/session_builder.py` — kolejka Incremental Rehearsal, warunek końca
- `engine/group_selector.py` — dobór grupy, obsługa edge case'ów
- `engine/anti_interference.py` — filtr podobnych faktów
- **Testy jednostkowe przed przejściem dalej**

### Etap 3 — Serwer
- `server.py` — endpointy, autosave co N odpowiedzi, zapis przy SIGTERM

### Etap 4 — UI dziecka
- Tryb klawiatury → tryb kafelków → animacje

### Etap 5 — UI rodzica
- Siatka → pudełka → historia → konfiguracja

### Etap 6 — Integracja i testy
- Pełny przepływ sesji
- Edge case'y: pierwszy start, restart serwera, pusta baza, sesja bez kart do powtórki

---

## Zależności Python

```
flask
```

Brak innych zewnętrznych zależności. Wszystkie dane w pamięci + JSON.
