"""Cały eksport naraz: projekt + programy świateł → gotowa sieć SUMO.

    1. model - .nod.xml / .edg.xml
    2. netconvert bez faz = numery połączeń (linkIndex)
    3. fazy - napisy stanów - .tll.xml
    4. netconvert z fazami - siec.net.xml
    5. weryfikacja faz na gotowej sieci (konflikty i ustępowanie z SUMO)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from junctio.model import Projekt
from .eksport_sumo import PlikiSumo, eksportuj_do_sumo, zbuduj_siec, BladEksportu
from .fazy import Problem, ProgramSwiatel, ma_bledy, sprawdz_program, zapisz_tll
from .skrzyzowanie_sumo import SkrzyzowanieSumo, wczytaj_skrzyzowanie


@dataclass
class WynikEksportu:
    siec: Path | None                     # None, gdy fazy mają błędy
    pliki: PlikiSumo
    skrzyzowania: dict[str, SkrzyzowanieSumo] = field(default_factory=dict)
    problemy: list[Problem] = field(default_factory=list)   # z weryfikacji faz
    ostrzezenia: list[str] = field(default_factory=list)    # z eksportu i netconvert

    @property
    def ok(self) -> bool:
        return self.siec is not None


def eksportuj_z_fazami(projekt: Projekt, programy: list[ProgramSwiatel],
                       katalog: str | Path, nazwa: str = "siec") -> WynikEksportu:
    katalog = Path(katalog)
    pliki = eksportuj_do_sumo(projekt, katalog, nazwa)
    # program świateł tylko dla węzła z rodzajem "swiatla", inaczej netconvert zwróci błąd
    wezly = {w.id: w for w in projekt.wezly}
    for p in programy:
        if p.wezel not in wezly or wezly[p.wezel].rodzaj != "swiatla":
            raise BladEksportu(
                f"Program świateł dla '{p.wezel}': ten węzeł nie ma rodzaju 'swiatla'")
    ostrzezenia = list(pliki.ostrzezenia)

    z_programem = {p.wezel for p in programy}
    for w in projekt.wezly:
        if w.rodzaj == "swiatla" and w.id not in z_programem:
            ostrzezenia.append(f"węzeł '{w.id}' ma światła bez naszego programu, "
                               "SUMO użyje domyślnego z netconvert")

    if not programy:
        wynik = zbuduj_siec(pliki)
        return WynikEksportu(wynik.siec, pliki, ostrzezenia=ostrzezenia + wynik.ostrzezenia)

    # sieć pomocnicza, tylko żeby poznać numery połączeń
    wstepna = zbuduj_siec(pliki, wyjscie=katalog / f"{nazwa}.bez_faz.net.xml")
    skrz = {p.wezel: wczytaj_skrzyzowanie(wstepna.siec, p.wezel) for p in programy}

    tll = zapisz_tll(programy, skrz, katalog / f"{nazwa}.tll.xml")
    koncowa = zbuduj_siec(pliki, programy_swiatel=tll)
    ostrzezenia += koncowa.ostrzezenia

    skrz = {p.wezel: wczytaj_skrzyzowanie(koncowa.siec, p.wezel) for p in programy}
    problemy = [pr for p in programy for pr in sprawdz_program(p, skrz[p.wezel])]

    siec = None if ma_bledy(problemy) else koncowa.siec
    return WynikEksportu(siec, pliki, skrz, problemy, ostrzezenia)
