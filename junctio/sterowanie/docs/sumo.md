# SUMO w projekcie

[SUMO](https://eclipse.dev/sumo/) to otwarty symulator ruchu drogowego. Używany do
do sprawdzania skrzyżowań i programów świateł na sprawdzonym silniku.

## Instalacja

```bash
pip install eclipse-sumo sumolib traci
netconvert --version        # powinno pokazać "Eclipse SUMO netconvert 1.x"
```

`eclipse-sumo` instaluje programy (`netconvert`, `sumo`, `sumo-gui`, `netedit`),
`sumolib` służy do czytania sieci w Pythonie, a `traci` do sterowania symulacją na żywo.
Jeśli `netconvert` nie jest w PATH (Windows bez aktywnego venv), kod i tak go znajdzie
przez pakiet `sumo` (`eksport_sumo.znajdz_program`).

## Jak SUMO opisuje sieć

| Plik | Zawartość | Kto go tworzy |
|---|---|---|
| `*.nod.xml` | węzły: id, x, y, typ skrzyżowania | nasz eksport |
| `*.edg.xml` | krawędzie: od, do, liczba pasów, prędkość, priorytet, kształt | nasz eksport |
| `*.tll.xml` | programy świateł (fazy) | nasz eksport (`fazy.zapisz_tll`) |
| `*.net.xml` | gotowa sieć: pasy, połączenia, kolizje, kształt skrzyżowań | `netconvert` |
| `*.rou.xml` | pojazdy i trasy | na razie ręcznie (`demo_sumo.py`) |

Najważniejsze różnice względem naszego modelu:

- krawędź SUMO jest jednokierunkowa, więc nasza `Droga` daje dwie: `id_tam` (od do)
  i `id_powrot` (do od, tylko gdy `pasy_powrot > 0`),
- pas 0 to skrajnie prawy pas,
- prędkość w m/s, nie w km/h,
- netconvert domyślnie przesuwa układ współrzędnych, my to wyłączamy, żeby x, y
  w SUMO były takie same jak w edytorze.

## Szybki start

```bash
python demo_sumo.py          # eksport przykładowego skrzyżowania, fazy, weryfikacja
python demo_sumo.py --gui    # to samo + symulacja w sumo-gui
```

## Użycie w kodzie

Same pliki węzłów i dróg (tak jak kazał lider 🫡):

```python
from sterowanie.eksport_sumo import eksportuj
eksportuj(projekt, "test")      # tworzy test.nod.xml i test.edg.xml
```

```bash
netconvert --node-files test.nod.xml --edge-files test.edg.xml -o test.net.xml --offset.disable-normalization true
sumo-gui -n test.net.xml
```

Całość z fazami świateł i weryfikacją:

```python
from sterowanie.fazy import Faza, ProgramSwiatel
from sterowanie.potok import eksportuj_z_fazami

# relacja = [droga wlotowa, droga wylotowa]; lewoskręty na zielonym warunkowym
program = ProgramSwiatel("C", fazy=[
    Faza("N-S", zielone=[["N", "S"], ["N", "W"], ["S", "N"], ["S", "E"]],
         warunkowe=[["N", "E"], ["S", "W"]], zielone_s=30),
    Faza("W-E", zielone=[["E", "W"], ["E", "N"], ["W", "E"], ["W", "S"]],
         warunkowe=[["E", "S"], ["W", "N"]], zielone_s=20),
])
wynik = eksportuj_z_fazami(projekt, [program], "wyniki_sumo")
for problem in wynik.problemy:
    print(problem)            # BŁĄD [N-S]: kolizja: ...
if wynik.ok:
    print("sieć:", wynik.siec)
```
