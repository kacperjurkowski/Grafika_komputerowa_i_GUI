"""Skrzyżowanie wpisane ręcznie, do testów eksportu i faz, zanim powstanie edytor.

          N (0, 100)
             │
 W (-100,0)──C──E (100, 0)      E ma lekki łuk, żeby sprawdzić kształt drogi
             │
          S (0, -100)

- C ma światła, N–S to droga główna.
- Wlot od S ma 2 pasy do skrzyżowania (sprawdzamy połączenia wielu pasów).
- Droga W jest zapisana "od C do W", odwrotnie niż pozostałe,
  żeby sprawdzić, czy eksport dobrze rozpoznaje kierunki.
"""
from model import Droga, Projekt, Wezel


def skrzyzowanie_4_wloty(rodzaj: str = "swiatla") -> Projekt:
    return Projekt(
        wezly=[
            Wezel("C", 0, 0, rodzaj),
            Wezel("N", 0, 100),
            Wezel("S", 0, -100),
            Wezel("E", 100, 0),
            Wezel("W", -100, 0),
        ],
        drogi=[
            Droga("N", od="N", do="C", glowna=True),
            Droga("S", od="S", do="C", pasy_tam=2, glowna=True),
            Droga("E", od="E", do="C", ksztalt=[(60, 8), (30, 4)]),
            Droga("W", od="C", do="W"),
        ],
    )
