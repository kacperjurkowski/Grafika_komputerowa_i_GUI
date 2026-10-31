"""Odczyt połączeń i konfliktów skrzyżowania z gotowej sieci SUMO (.net.xml).

netconvert dla każdego skrzyżowania wylicza:
- połączenia (connection): który pas wlotu łączy się z którym pasem wylotu,
  każde ma numer linkIndex, czyli swoją pozycję w napisie stanu światel,
- kolizje (foes): pary połączeń, których tory się przecinają albo łączą,
- ustępowanie (response): które połączenie musi przepuścić które. Na skrzyżowaniu
  ze światłami netconvert liczy to z uwzględnieniem programu, więc do sprawdzania
  faz czyta sie sieć zbudowaną już z programem.

"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import sumolib

from eksport_sumo import (droga_z_krawedzi)

KIERUNKI = {
    "s": "prosto",
    "l": "w lewo",
    "r": "w prawo",
    "t": "zawracanie",
    "L": "lekko w lewo",
    "R": "lekko w prawo",
}

Relacja = tuple[str, str]  # (id drogi wlotowej, id drogi wylotowej)


@dataclass(frozen=True)
class Polaczenie:
    indeks: int        # pozycja w napisie stanu świateł (linkIndex)
    wlot: str          # id drogi z modelu, którą auto wjeżdża
    wylot: str         # id drogi z modelu, którą auto wyjeżdża
    kierunek: str      # kod SUMO: s, l, r, t, L, R
    pas: int           # numer pasa na wlocie (0 = skrajnie prawy)
    krawedz_z: str     # id krawędzi SUMO
    krawedz_do: str
    kat_wlotu: float   # kierunek jazdy przy wjeździe, w stopniach (0 = na wschód, 90 = na północ)

    @property
    def relacja(self) -> Relacja:
        return (self.wlot, self.wylot)

    @property
    def kierunek_opis(self) -> str:
        return KIERUNKI.get(self.kierunek, self.kierunek)


@dataclass(frozen=True)
class SkrzyzowanieSumo:
    wezel: str
    typ: str                                   # typ węzła w SUMO, np. traffic_light
    polaczenia: tuple[Polaczenie, ...]         # posortowane po indeksie
    kolizje: frozenset[frozenset[int]]         # pary indeksów, których tory się spotykają
    ustepuje: frozenset[tuple[int, int]]       # (a, b): a musi przepuścić b

    def relacje(self) -> list[Relacja]:
        # wszystkie relacje w kolejności pierwszego indeksu.
        wynik: list[Relacja] = []
        for p in self.polaczenia:
            if p.relacja not in wynik:
                wynik.append(p.relacja)
        return wynik

    def indeksy(self, relacja: Relacja) -> list[int]:
        return [p.indeks for p in self.polaczenia if p.relacja == tuple(relacja)]

    def koliduja(self, a: int, b: int) -> bool:
        return frozenset((a, b)) in self.kolizje

    def polaczenie(self, indeks: int) -> Polaczenie:
        return next(p for p in self.polaczenia if p.indeks == indeks)

    def z_naprzeciwka(self, a: int, b: int) -> bool:
        # czy połączenia a i b zaczynają się na wlotach naprzeciw siebie (różnica kierunków > 135
        roznica = abs(self.polaczenie(a).kat_wlotu - self.polaczenie(b).kat_wlotu) % 360
        return min(roznica, 360 - roznica) > 135

    def kierunek_relacji(self, relacja: Relacja) -> str:
        for p in self.polaczenia:
            if p.relacja == tuple(relacja):
                return p.kierunek_opis
        return "?"

    @property
    def liczba_sygnalow(self) -> int:
        # dlugość napisu stanu świateł dla tego skrzyżowania
        return max((p.indeks for p in self.polaczenia), default=-1) + 1


def wczytaj_skrzyzowanie(siec: str | Path, wezel_id: str) -> SkrzyzowanieSumo:
    # czyta połączenia i macierz konfliktów jednego węzła z pliku .net.xml
    net = sumolib.net.readNet(str(siec), withPrograms=True)
    if not net.hasNode(wezel_id):
        raise KeyError(f"W sieci nie ma węzła '{wezel_id}'")
    wezel = net.getNode(wezel_id)
    swiatla = wezel.getType().startswith("traffic_light")

    # indeks w skrzyżowaniu (do macierzy foes) i indeks w programie świateł
    # (linkIndex) zwykle są równe, ale nie musi tak być, więc mapujemy jawnie.
    sumo_polaczenia = {}   # nasz indeks - (indeks w węźle, obiekt połączenia sumolib)
    polaczenia = []
    for c in wezel.getConnections():
        if c.getFrom().getFunction() or c.getTo().getFunction():
            continue  # pominiecie przejścia dla pieszych i chodniki (na razie ich nie ma)
        i_wezla = wezel.getLinkIndex(c)
        indeks = c.getTLLinkIndex() if swiatla and c.getTLLinkIndex() >= 0 else i_wezla
        sumo_polaczenia[indeks] = (i_wezla, c)
        (x1, y1), (x2, y2) = c.getFrom().getShape()[-2:]   # ostatni odcinek przed węzłem
        polaczenia.append(Polaczenie(
            indeks=indeks,
            wlot=droga_z_krawedzi(c.getFrom().getID()),
            wylot=droga_z_krawedzi(c.getTo().getID()),
            kierunek=c.getDirection(),
            pas=c.getFromLane().getIndex(),
            krawedz_z=c.getFrom().getID(),
            krawedz_do=c.getTo().getID(),
            kat_wlotu=round(math.degrees(math.atan2(y2 - y1, x2 - x1)) % 360, 1),
        ))
    polaczenia.sort(key=lambda p: p.indeks)

    kolizje = set()
    ustepuje = set()
    if wezel.hasFoes():
        for a, (wa, ca) in sumo_polaczenia.items():
            for b, (wb, cb) in sumo_polaczenia.items():
                if a == b:
                    continue
                if wezel.areFoes(wa, wb):
                    kolizje.add(frozenset((a, b)))
                if wezel.forbids(cb, ca):      # b zabrania przejazdu a - a ustępuje b
                    ustepuje.add((a, b))

    return SkrzyzowanieSumo(wezel_id, wezel.getType(), tuple(polaczenia),
                            frozenset(kolizje), frozenset(ustepuje))
