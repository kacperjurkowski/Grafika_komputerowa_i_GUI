# fazy świateł, czasy sygnałów, program dla SUMO i weryfikacja konfliktów.


from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from skrzyzowanie_sumo import Relacja, SkrzyzowanieSumo

ZOLTE_PRZEPISY_S = 3.0 #chyba tak jest w przepisach zolte przed czerwonym
MIN_ZIELONE_S = 5.0
MIN_WSZYSTKIE_CZERWONE_S = 1.0

ZIELONE = "Gg"
JADA = "Ggy"          # stany w których można wjechać na skrzyżowanie


# ---------------------------------------------------------------- dane

@dataclass
class Faza:
    nazwa: str
    zielone: list = field(default_factory=list)     # [[wlot, wylot], ...] z pierwszeństwem (G)
    warunkowe: list = field(default_factory=list)   # [[wlot, wylot], ...] z ustąpieniem (g)
    zielone_s: float = 20.0
    zolte_s: float = ZOLTE_PRZEPISY_S
    wszystkie_czerwone_s: float = 2.0               # po żółtym, przed następną fazą

    def stan_relacji(self, relacja: Relacja) -> str:
        relacja = tuple(relacja)
        if relacja in {tuple(r) for r in self.zielone}:
            return "G"
        if relacja in {tuple(r) for r in self.warunkowe}:
            return "g"
        return "r"


@dataclass
class ProgramSwiatel:
    wezel: str                                      # id węzła z rodzajem "swiatla"
    fazy: list = field(default_factory=list)        # list[Faza]
    czerwone_zolte_s: float = 1.0                   # sygnał czerwony z żółtym przed zielonym
    przesuniecie_s: float = 0.0                     # offset cyklu (do koordynacji kilku skrzyżowań)


@dataclass(frozen=True)
class Stan:
    # jeden krok programu SUMO: przez `czas_s` świeci napis `stan`.
    nazwa: str
    czas_s: float
    stan: str          # jeden znak na połączenie, indeks = linkIndex


@dataclass(frozen=True)
class Problem:
    poziom: str        # "blad" albo "ostrzezenie"
    komunikat: str
    faza: str | None = None

    def __str__(self) -> str:
        znak = "BŁĄD" if self.poziom == "blad" else "uwaga"
        gdzie = f" [{self.faza}]" if self.faza else ""
        return f"{znak}{gdzie}: {self.komunikat}"


# ---------------------------------------------------------------- budowa stanów

def _stany_fazy(faza: Faza, skrz: SkrzyzowanieSumo) -> list[str]:
    # stan każdego połączenia (G/g/r) w zielonym tej fazy
    stany = ["r"] * skrz.liczba_sygnalow
    for p in skrz.polaczenia:
        stany[p.indeks] = faza.stan_relacji(p.relacja)
    return stany


def zbuduj_stany(program: ProgramSwiatel, skrz: SkrzyzowanieSumo) -> list[Stan]:
    # rozpiska programu na kolejne stany SUMO łącznie z przejściami między fazami
    if not program.fazy:
        return []
    zielone = [_stany_fazy(f, skrz) for f in program.fazy]
    n = len(program.fazy)
    wynik: list[Stan] = []

    for i, faza in enumerate(program.fazy):
        teraz, potem = zielone[i], zielone[(i + 1) % n]
        wynik.append(Stan(faza.nazwa, faza.zielone_s, "".join(teraz)))

        konczy = [a in ZIELONE and b not in ZIELONE for a, b in zip(teraz, potem)]
        zaczyna = [a not in ZIELONE and b in ZIELONE for a, b in zip(teraz, potem)]
        if not any(konczy) and not any(zaczyna):
            continue  # nic się nie zmienia (np. program z jedną fazą)

        def przejscie(dla_konczacych: str, dla_zaczynajacych: str) -> str:
            znaki = []
            for a, b, k, z in zip(teraz, potem, konczy, zaczyna):
                if k:
                    znaki.append(dla_konczacych)
                elif z:
                    znaki.append(dla_zaczynajacych)
                elif a in ZIELONE:          # zielone w obu fazach: świeci dalej
                    znaki.append(a)
                else:
                    znaki.append("r")
            return "".join(znaki)

        nastepna = program.fazy[(i + 1) % n].nazwa
        kroki = [
            (f"{faza.nazwa}: żółte", faza.zolte_s, przejscie("y", "r")),
            (f"{faza.nazwa}: wszystkie czerwone", faza.wszystkie_czerwone_s, przejscie("r", "r")),
            (f"{nastepna}: czerwone z żółtym", program.czerwone_zolte_s, przejscie("r", "u")),
        ]
        wynik += [Stan(nazwa, czas, stan) for nazwa, czas, stan in kroki if czas > 0]
    return wynik


def czas_cyklu(program: ProgramSwiatel, skrz: SkrzyzowanieSumo) -> float:
    return sum(s.czas_s for s in zbuduj_stany(program, skrz))


def czasy_relacji(program: ProgramSwiatel, skrz: SkrzyzowanieSumo) -> dict[Relacja, dict[str, float]]:
    # ile sekund w cyklu każda relacja ma zielone, żółte, czerwone i czerwone z żółtym
    stany = zbuduj_stany(program, skrz)
    wynik = {}
    for relacja in skrz.relacje():
        i = skrz.indeksy(relacja)[0]   # wszystkie pasy relacji mają ten sam sygnał
        czasy = {"zielone": 0.0, "zolte": 0.0, "czerwone": 0.0, "czerwone_zolte": 0.0}
        for s in stany:
            klucz = {"G": "zielone", "g": "zielone", "y": "zolte", "u": "czerwone_zolte"}.get(
                s.stan[i], "czerwone")
            czasy[klucz] += s.czas_s
        wynik[relacja] = czasy
    return wynik


# weryfikacja

def _opis(skrz: SkrzyzowanieSumo, indeks: int) -> str:
    p = next(p for p in skrz.polaczenia if p.indeks == indeks)
    return f"{p.wlot}→{p.wylot} ({p.kierunek_opis})"


def _kolizja_drugorzedna(skrz: SkrzyzowanieSumo, stany: list[str], skrecajacy: int, drugi: int) -> bool:
    # czy kolizja jest dopuszczalna: lewoskręt na zielonym warunkowym ustępuje jadącym z naprzeciwka
    return (stany[skrecajacy] == "g"
            and skrz.polaczenie(skrecajacy).kierunek in ("l", "L")
            and skrz.z_naprzeciwka(skrecajacy, drugi)
            and (skrecajacy, drugi) in skrz.ustepuje)


def sprawdz_program(program: ProgramSwiatel, skrz: SkrzyzowanieSumo) -> list[Problem]:
    """Sprawdza program świateł. Błędy blokują zapis, ostrzeżenia tylko informują.

    Reguła konfliktów: dwa połączenia, których tory się spotykają (foes z SUMO),
    mogą mieć zielone jednocześnie tylko w jednym przypadku: lewoskręt na zielonym
    warunkowym ('g') i jadący z naprzeciwka, przy czym SUMO potwierdza, że lewoskręt
    ustępuje. Wszystkie inne pary kolidujących relacji muszą być w różnych fazach.
    """
    problemy: list[Problem] = []

    def blad(tekst, faza=None):
        problemy.append(Problem("blad", tekst, faza))

    def uwaga(tekst, faza=None):
        problemy.append(Problem("ostrzezenie", tekst, faza))

    # program jako całość
    if skrz.wezel != program.wezel:
        blad(f"program dotyczy węzła '{program.wezel}', a sprawdzane skrzyżowanie to '{skrz.wezel}'")
    if not skrz.typ.startswith("traffic_light"):
        blad(f"węzeł '{skrz.wezel}' nie ma świateł (typ SUMO: {skrz.typ}), ustaw rodzaj 'swiatla'")
    if not program.fazy:
        blad("program nie ma żadnej fazy")
        return problemy
    if program.czerwone_zolte_s < 0:
        blad("czas czerwonego z żółtym nie może być ujemny")

    istniejace = set(skrz.relacje())
    nazwy = [f.nazwa for f in program.fazy]
    for nazwa in {n for n in nazwy if nazwy.count(n) > 1}:
        blad(f"nazwa fazy '{nazwa}' powtarza się")

    # każda faza osobno
    for faza in program.fazy:
        if faza.zielone_s <= 0:
            blad("czas zielonego musi być dodatni", faza.nazwa)
        elif faza.zielone_s < MIN_ZIELONE_S:
            uwaga(f"zielone {faza.zielone_s:g} s to mniej niż przyjęte minimum {MIN_ZIELONE_S:g} s", faza.nazwa)
        if faza.zolte_s < 0 or faza.wszystkie_czerwone_s < 0:
            blad("czasy żółtego i wszystkich czerwonych nie mogą być ujemne", faza.nazwa)
        elif faza.zolte_s != ZOLTE_PRZEPISY_S and len(program.fazy) > 1:
            uwaga(f"żółte trwa {faza.zolte_s:g} s, a polskie przepisy wymagają {ZOLTE_PRZEPISY_S:g} s", faza.nazwa)

        zielone = {tuple(r) for r in faza.zielone}
        warunkowe = {tuple(r) for r in faza.warunkowe}
        for r in sorted(zielone & warunkowe):
            blad(f"relacja {r[0]}→{r[1]} jest jednocześnie w zielonych i warunkowych", faza.nazwa)
        for r in sorted((zielone | warunkowe) - istniejace):
            blad(f"relacja {r[0]}→{r[1]} nie istnieje na tym skrzyżowaniu", faza.nazwa)

        # kolizje w zielonym tej fazy
        stany = _stany_fazy(faza, skrz)
        jada = [i for i, s in enumerate(stany) if s in JADA]
        zgloszone = set()
        for a, b in combinations(jada, 2):
            if not skrz.koliduja(a, b):
                continue
            ra = next(p.relacja for p in skrz.polaczenia if p.indeks == a)
            rb = next(p.relacja for p in skrz.polaczenia if p.indeks == b)
            if frozenset((ra, rb)) in zgloszone:
                continue   # ta sama para relacji na innym pasie
            if _kolizja_drugorzedna(skrz, stany, a, b) or _kolizja_drugorzedna(skrz, stany, b, a):
                continue
            zgloszone.add(frozenset((ra, rb)))
            if "g" not in (stany[a], stany[b]):
                powod = "obie mają pełne zielone"
            elif skrz.z_naprzeciwka(a, b):
                powod = "zielone warunkowe dostaje tylko lewoskręt ustępujący jadącym z naprzeciwka"
            else:
                powod = ("to kolizja kierunków poprzecznych, takich relacji nie puszcza się razem "
                         "nawet na zielonym warunkowym")
            blad(f"kolizja: {_opis(skrz, a)} i {_opis(skrz, b)}: {powod}", faza.nazwa)

        # pas z kilkoma relacjami, czerwone dla jednej zablokuje pozostałe
        pasy: dict[tuple[str, int], list] = {}
        for p in skrz.polaczenia:
            pasy.setdefault((p.krawedz_z, p.pas), []).append(p)
        for (krawedz, pas), na_pasie in pasy.items():
            jedzie = {p.relacja for p in na_pasie if stany[p.indeks] in JADA}
            stoi = {p.relacja for p in na_pasie if stany[p.indeks] not in JADA}
            if jedzie and stoi:
                uwaga(f"pas {pas} wlotu {na_pasie[0].wlot} jest wspólny dla "
                      f"{', '.join(f'{a}→{b}' for a, b in sorted(jedzie | stoi))}, "
                      f"a zielone ma tylko część z nich; auto czekające na czerwonym "
                      f"zablokuje pas", faza.nazwa)

    # relacje bez zielonego w całym cyklu
    kiedykolwiek = set()
    for faza in program.fazy:
        kiedykolwiek |= {tuple(r) for r in faza.zielone} | {tuple(r) for r in faza.warunkowe}
    for r in skrz.relacje():
        if r not in kiedykolwiek:
            uwaga(f"relacja {r[0]}→{r[1]} ({skrz.kierunek_relacji(r)}) nie ma zielonego w żadnej fazie")

    # przejścia między fazami, kolidujące relacje bez przerwy na wszystkie czerwone
    if len(program.fazy) > 1:
        for i, faza in enumerate(program.fazy):
            nastepna = program.fazy[(i + 1) % len(program.fazy)]
            teraz, potem = _stany_fazy(faza, skrz), _stany_fazy(nastepna, skrz)
            konczy = [k for k in range(len(teraz)) if teraz[k] in ZIELONE and potem[k] not in ZIELONE]
            zaczyna = [k for k in range(len(teraz)) if teraz[k] not in ZIELONE and potem[k] in ZIELONE]
            kolidujace = [(a, b) for a in konczy for b in zaczyna if skrz.koliduja(a, b)]
            if kolidujace and faza.wszystkie_czerwone_s < MIN_WSZYSTKIE_CZERWONE_S:
                a, b = kolidujace[0]
                uwaga(f"przejście do '{nastepna.nazwa}': {_opis(skrz, a)} kończy, a kolidujące "
                      f"{_opis(skrz, b)} zaczyna, przy wszystkich czerwonych tylko "
                      f"{faza.wszystkie_czerwone_s:g} s; auto z żółtego może nie zdążyć zjechać",
                      faza.nazwa)
    return problemy


def ma_bledy(problemy: list[Problem]) -> bool:
    return any(p.poziom == "blad" for p in problemy)


# JSON

def program_do_dict(program: ProgramSwiatel) -> dict:
    # do zapisu w pliku projektu json.dump
    from dataclasses import asdict
    d = asdict(program)
    for f in d["fazy"]:
        f["zielone"] = [list(r) for r in f["zielone"]]
        f["warunkowe"] = [list(r) for r in f["warunkowe"]]
    return d


def program_z_dict(d: dict) -> ProgramSwiatel:
    # odwrotność program_do_dict (po json.load)
    d = dict(d)
    d["fazy"] = [Faza(**f) for f in d.get("fazy", [])]
    return ProgramSwiatel(**d)


# zapis dla SUMO

def zapisz_tll(programy: list[ProgramSwiatel], skrzyzowania: dict[str, SkrzyzowanieSumo],
               sciezka: str | Path) -> Path:
    # Zapisuje programy świateł jako plik .tll.xml dla netconvert (--tllogic-files).

    korzen = ET.Element("tlLogics")
    for program in programy:
        skrz = skrzyzowania[program.wezel]
        tl = ET.SubElement(korzen, "tlLogic", {
            "id": program.wezel, "type": "static", "programID": "0",
            "offset": f"{program.przesuniecie_s:g}",
        })
        for s in zbuduj_stany(program, skrz):
            ET.SubElement(tl, "phase", {"duration": f"{s.czas_s:g}", "state": s.stan, "name": s.nazwa})
    ET.indent(korzen, space="    ")
    sciezka = Path(sciezka)
    ET.ElementTree(korzen).write(sciezka, encoding="utf-8", xml_declaration=True)
    return sciezka
