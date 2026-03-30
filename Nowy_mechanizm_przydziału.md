
Modufikacja mechanizumu przydziału kart do nauki, zgodnie z ponizszymi zaleceniami.

1. Zaraz po uruchomieniu programu, gdy nie ma jeszcze rezultatów pokazujących znajomość wyników w "Sytem Leitnera 5 pudełek" dla kazdej karty:
-  kolejne zestawy kart w sesji generowane są tylko na podstawie definicji grup opisanych w RAW_GROUPS w kolejności grup określonych w INTRODUCTION_ORDER
-  grupa musi być nauczana co najmniej dwa razy o ile udzielono odpowiedzi poprawnych dla wszystkich kart tej grupy
    -  o ile przynajmniej jedna karat miała odpowiedź błędną , grupa podawana jest do nauki kolejny raz. 
    - proces uczenia grupy koczy się gdy co najmniej dwie kolejne sesje były bezgłędne, wtedy wybierana jest kolejna grupa z INTRODUCTION_ORDER i uczona zgodnie z opisaną prcedurą.

- "System Leitnera 5 pudełek" nie ma w tej fazie zastosowania w doborze kart do nauki ale słuzy do zapisywania rezultatów.
    - Poprawna odpowiedź → przesuń do box+1 (max 5)
    - Błędna odpowiedź → cofnij do box 1
    - Karty 2×3 i 3×2 są **całkowicie niezależne** — błąd w jednej nie wpływa na drugą.
    - UWAGA: brak kryterium czasu odpowidzi, decyduje tylko to czy odpowiedz jest poprawna.


2. Kiedy wszystkie grupy zostały juz poddane nauczaniu o wyborze kart do nauki decyduje system "Sytem Leitnera 5 pudełek".
- UWAGA: Modyfikacja rozumienia pudełek polega na tym, ze nie ma juz powiazania z czasem (chodzi mi o naukę jutro, po jutrze czy za 5 dni)
    - Pudełka określają teraz częstotliwość nauki w skali od 1 do 5. 1 to największa częstotliwość nauki.
- W tej fazie dobierane są do powtórzeń karty zgodnie z określoną częstotliwością, nie ma juz powiazania z systemem grup określonym w RAW_GROUPS i INTRODUCTION_ORDER.
    - Algorytm tworzy kopię pudełka (zbiór) z kórego dobierane są karty do nauki.
        - Dobrane karty usuwane są z tego zbioru, ma to zapewnić ze przechodzimy tyko raz przez zbiór kart w pudełku a wyniki bierzącej nauki nie mają wypłu na kolejny dobór kart.
    - Algortym losuje 4 karty z pudełka "1" (jego kopii), jezeli brakuje kart w pudełku "1" to dobiera z pudełka "2" itd.
        - utworzona grupa uczona jest co najmniej dwa razy o ile udzielono odpowiedzi poprawnych dla wszystkich kart tej grupy
            - o ile przynajmniej jedna karat miała odpowiedź błędną grupa podawana jest do nauki kolejny raz. 
            -proces uczenia grupy koczy się gdy co najmniej dwie kolejne sesje były bezgłędne, wtedy losowana jest kolejna grupa.
    - cały czas zalenie od udzielonych odpowiedzi (poprawnych i błędnych) karty przesówane są miedzy pudełkami

    - Zmiany pudełka dla doboru kart do nauki.
        - Kiedy przejdziemy przez wszyskie karty z jednego pudełka np: "1" (jego kopia jest juz pusta) przechodzimy do kolejnego czyli "2" i powtwrzamy cały proces, następnie wracamy do pudełka "1"
        - Pudełko numer "1" powinno być wybierane co drugi raz czyli "1", X, "1". Gdzie pudełko X to 2, 3, 4 i 5 z odpowiednio pomniejszonymi częstotliwościami. 
            - Pudełko numer 2 wraca najczęściej a 5 najrzadziej.
            - jezeli w pudełku nie ma kart do nauki to wybierane jest kolejne 
        - Jezeli w pudełku "1" nie ma zadnych kart to pudełko numer "2" staje się tym o największejsz częstotliwość nauki i wybierane jest co drugi raz, chyby ze nie ma w nim kart wtedy wybierane jest kolejne pudełko z kartami.

3. System logowania:
- Chciałbym zeby w konsoli pokazywały sie logi pokazujące np: wybrana grupa z RAW_GROUPS lub wybrane pudełko, wybrane karty i te które jeszcze zostały.

4. Panel rodzica:
- Zakładaka "pudełka" powinna pokazywać pudełka i karty które się w nich znajdują
- Zakładka "ustawienia", następujace elementy nie maja sensu przy zmiane algorytmu i mogą być usunięte:
    - "Sugestia algorytmu" - algorytm jest obecnie jasno opisany i nie podlega modyfikacją
    - "Próg opanowania (ms)
    - "Autosave co N odpowiedzi" - autosave powinien być po kazdej sesji - 4 karty
    -  Nowe karty / sesja
    -  Twardy limit (min)
    -  Długość sesji (min)

- Zostaje tylko: "Tryb odpowiedzi" w domyśle jest to kalawiatura jak obecnie

5. Panel dziecka
- w zasadzie bez zmian. 

        
               
```
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

# Kolejność wprowadzania grup przez algorytm
INTRODUCTION_ORDER = [
    "A1", "A3", "A2", "A4",
    "B1", "B3", "B2", "B4",
    "C1", "C3", "C2", "C4",
    "D1", "D3", "D2", "D4",
]

```