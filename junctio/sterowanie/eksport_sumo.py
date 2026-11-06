# Eksport modelu projektu do plików SUMO i budowa sieci netconvertem.

from __future__ import annotations

import shutil
import subprocess
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from model import Droga, Projekt, Wezel

# rodzaj węzła w modelu - typ węzła w SUMO
TYP_WEZLA_SUMO = {
    "brak": "right_before_left",
    "swiatla": "traffic_light",
    "pierwszenstwo": "priority",
    "stop": "priority_stop",
    "stop_wszystkie": "allway_stop",
}

# priorytet krawędzi decyduje, która droga główna na skrzyżowaniu
PRIORYTET_GLOWNA = 2
PRIORYTET_ZWYKLA = 1

# Opcje netconvert
OPCJE_NETCONVERT = [
    "--offset.disable-normalization", "true",  # nie przesuwanie współrzędnych do (0, 0)
    "--no-turnarounds", "true",                # na ten moment bez zawracania
    "--junctions.corner-detail", "5",          # zaokrąglone narożniki skrzyżowań
    "--tls.default-type", "static",            # stały cykl świateł
]


class BladEksportu(ValueError):
    """projekt nie da się wyeksportować do SUMO błędne dane lub błąd netconvert"""


@dataclass
class PlikiSumo:
    wezly: Path        # *.nod.xml
    drogi: Path        # *.edg.xml
    ostrzezenia: list[str] = field(default_factory=list)


@dataclass
class WynikNetconvert:
    siec: Path         # *.net.xml
    ostrzezenia: list[str] = field(default_factory=list)


# nazwy krawędzi

PRZYROSTEK_TAM = "_tam"
PRZYROSTEK_POWROT = "_powrot"


def id_krawedzi(droga_id: str, w_strone_do: bool = True) -> str:
    # Id krawędzi SUMO dla danego kierunku drogi
    return droga_id + (PRZYROSTEK_TAM if w_strone_do else PRZYROSTEK_POWROT)


def droga_z_krawedzi(krawedz_id: str) -> str:
    # odwrotność id_krawedzi z id krawędzi SUMO zwraca id drogi z modelu
    for przyrostek in (PRZYROSTEK_TAM, PRZYROSTEK_POWROT):
        if krawedz_id.endswith(przyrostek):
            return krawedz_id[: -len(przyrostek)]
    return krawedz_id


# walidacja

def _zle_id(id_: str) -> str | None:
    if not id_:
        return "puste id"
    if id_.startswith(":"):
        return "id nie może zaczynać się od ':' (zarezerwowane w SUMO)"
    if any(z.isspace() for z in id_):
        return "id nie może zawierać spacji"
    return None


def sprawdz_projekt(projekt: Projekt) -> list[str]:
    # Sprawdza, czy projekt da się wyeksportować.

    bledy: list[str] = []
    ostrzezenia: list[str] = []

    wezly: dict[str, Wezel] = {}
    for w in projekt.wezly:
        if (p := _zle_id(w.id)):
            bledy.append(f"węzeł '{w.id}': {p}")
        if w.id in wezly:
            bledy.append(f"węzeł '{w.id}' występuje dwa razy")
        if w.rodzaj not in TYP_WEZLA_SUMO:
            bledy.append(f"węzeł '{w.id}': nieznany rodzaj '{w.rodzaj}' "
                         f"(dozwolone: {', '.join(TYP_WEZLA_SUMO)})")
        wezly[w.id] = w

    widziane_drogi: set[str] = set()
    for d in projekt.drogi:
        if (p := _zle_id(d.id)):
            bledy.append(f"droga '{d.id}': {p}")
        if d.id in widziane_drogi:
            bledy.append(f"droga '{d.id}' występuje dwa razy")
        widziane_drogi.add(d.id)
        for koniec in (d.od, d.do):
            if koniec not in wezly:
                bledy.append(f"droga '{d.id}': nie ma węzła '{koniec}'")
        if d.od == d.do:
            bledy.append(f"droga '{d.id}': zaczyna się i kończy w tym samym węźle")
        if d.pasy_tam < 0 or d.pasy_powrot < 0:
            bledy.append(f"droga '{d.id}': ujemna liczba pasów")
        if d.pasy_tam == 0 and d.pasy_powrot == 0:
            bledy.append(f"droga '{d.id}': brak pasów w obu kierunkach")
        if d.predkosc_kmh <= 0:
            bledy.append(f"droga '{d.id}': prędkość musi być dodatnia")
        for pkt in d.ksztalt:
            if len(pkt) != 2:
                bledy.append(f"droga '{d.id}': punkt kształtu {pkt} nie jest parą (x, y)")
                break

    if bledy:
        raise BladEksportu("Projekt ma błędy:\n- " + "\n- ".join(bledy))

    # ostrzeżenia które da się policzyć dopiero przy poprawnych danych
    for w in projekt.wezly:
        drogi_wezla = [d for d in projekt.drogi if w.id in (d.od, d.do)]
        if not drogi_wezla:
            ostrzezenia.append(f"węzeł '{w.id}' nie ma żadnej drogi, netconvert go usunie")
        elif len(drogi_wezla) == 1 and w.rodzaj != "brak":
            ostrzezenia.append(f"węzeł '{w.id}' to koniec drogi, rodzaj '{w.rodzaj}' nic tu "
                               "nie reguluje (najwyżej zawracanie)")
        elif w.rodzaj in ("pierwszenstwo", "stop"):
            glowne = sum(d.glowna for d in drogi_wezla)
            if glowne != 2:
                ostrzezenia.append(
                    f"węzeł '{w.id}' ({w.rodzaj}): {glowne} dróg głównych zamiast 2, "
                    "SUMO wybierze drogę z pierwszeństwem samo (po prędkości i liczbie pasów)")
    return ostrzezenia


# eksport

def _liczba(v: float) -> str:
    return f"{float(v):.2f}"


def _punkt(x: float, y: float) -> str:
    return f"{_liczba(x)},{_liczba(y)}"


def _zapisz_xml(korzen: ET.Element, sciezka: Path) -> None:
    ET.indent(korzen, space="    ")
    ET.ElementTree(korzen).write(sciezka, encoding="utf-8", xml_declaration=True)


def eksportuj_do_sumo(projekt: Projekt, katalog: str | Path, nazwa: str = "siec") -> PlikiSumo:
    # zapis projektu na pliki węzłów .nod.xml)i dróg .edg.xml SUMO
    ostrzezenia = sprawdz_projekt(projekt)
    katalog = Path(katalog)
    katalog.mkdir(parents=True, exist_ok=True)

    wezly = {w.id: w for w in projekt.wezly}

    # węzły: każdy z id, x, y i typem z tabeli
    nodes = ET.Element("nodes")
    for w in projekt.wezly:
        ET.SubElement(nodes, "node", {"id": w.id, "x": _liczba(w.x), "y": _liczba(w.y),
                                      "type": TYP_WEZLA_SUMO[w.rodzaj]})

    # drogi: każda droga to jedna lub dwie krawędzie
    edges = ET.Element("edges")
    for d in projekt.drogi:
        a, b = wezly[d.od], wezly[d.do]
        punkty = [(a.x, a.y), *[tuple(p) for p in d.ksztalt], (b.x, b.y)]
        # dwukierunkowa: pasy na prawo od osi drogi, jednokierunkowa: pasy na osi
        rozklad = "right" if d.pasy_tam and d.pasy_powrot else "center"

        for w_strone_do, pasy in ((True, d.pasy_tam), (False, d.pasy_powrot)):
            if pasy == 0:
                continue
            atrybuty = {
                "id": id_krawedzi(d.id, w_strone_do),
                "from": d.od if w_strone_do else d.do,
                "to": d.do if w_strone_do else d.od,
                "numLanes": str(pasy),
                "speed": _liczba(d.predkosc_kmh / 3.6),
                "priority": str(PRIORYTET_GLOWNA if d.glowna else PRIORYTET_ZWYKLA),
                "spreadType": rozklad,
            }
            if d.ksztalt:
                # SUMO potrzebuje kształt z punktem początkowym i końcowym
                pkt = punkty if w_strone_do else list(reversed(punkty))
                atrybuty["shape"] = " ".join(_punkt(x, y) for x, y in pkt)
            ET.SubElement(edges, "edge", atrybuty)

    pliki = PlikiSumo(katalog / f"{nazwa}.nod.xml", katalog / f"{nazwa}.edg.xml", ostrzezenia)
    _zapisz_xml(nodes, pliki.wezly)
    _zapisz_xml(edges, pliki.drogi)
    return pliki


def eksportuj(projekt: Projekt, nazwa: str) -> None:
    # tworzenie pliki {nazwa}.nod.xml i {nazwa}.edg.xml.

    sciezka = Path(nazwa)
    pliki = eksportuj_do_sumo(projekt, sciezka.parent, sciezka.name)
    for o in pliki.ostrzezenia:
        warnings.warn(o, stacklevel=2)


# ---------------------------------------------------------------- netconvert

def znajdz_program(nazwa: str) -> str:
    # ścieżka do programu SUMO, netconvert, sumo, sumo-gui zainstalowanego przez pip
    if (sciezka := shutil.which(nazwa)):
        return sciezka
    try:
        import sumo
        for kandydat in (Path(sumo.SUMO_HOME) / "bin" / nazwa,
                         Path(sumo.SUMO_HOME) / "bin" / f"{nazwa}.exe"):
            if kandydat.exists():
                return str(kandydat)
    except ImportError:
        pass
    raise BladEksportu(f"Nie znaleziono '{nazwa}'. Zainstaluj SUMO: pip install eclipse-sumo")


def zbuduj_siec(pliki: PlikiSumo, programy_swiatel: str | Path | None = None,
                wyjscie: str | Path | None = None) -> WynikNetconvert:
    # Uruchamia netconvert i zwraca ścieżkę do gotowej sieci .net.xml.

    siec = Path(wyjscie) if wyjscie else pliki.wezly.with_name(
        pliki.wezly.name.replace(".nod.xml", ".net.xml"))
    polecenie = [
        znajdz_program("netconvert"),
        "--node-files", str(pliki.wezly),
        "--edge-files", str(pliki.drogi),
        "--output-file", str(siec),
        *OPCJE_NETCONVERT,
    ]
    if programy_swiatel:
        polecenie += ["--tllogic-files", str(programy_swiatel)]

    wynik = subprocess.run(polecenie, capture_output=True, text=True)
    komunikaty = (wynik.stdout + wynik.stderr).splitlines()
    if wynik.returncode != 0:
        raise BladEksportu("netconvert zakończył się błędem:\n" + "\n".join(komunikaty))
    ostrzezenia = [k for k in komunikaty if k.startswith("Warning")]
    return WynikNetconvert(siec, ostrzezenia)
