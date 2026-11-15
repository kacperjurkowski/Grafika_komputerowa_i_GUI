# Demo: ręcznie wpisane skrzyżowanie → SUMO, z naszymi fazami świateł.
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .eksport_sumo import id_krawedzi, znajdz_program
from .fazy import Faza, ProgramSwiatel, czas_cyklu, czasy_relacji, zbuduj_stany
from .potok import eksportuj_z_fazami
from .przyklad import skrzyzowanie_4_wloty

KATALOG = Path(__file__).resolve().parents[2] / "sumo_out"

# dwie fazy najpierw N-S potem W-E skret w lewo na warunkowym
PROGRAM_DOBRY = ProgramSwiatel("C", fazy=[
    Faza("Faza 1: N-S",
         zielone=[["N", "S"], ["N", "W"], ["S", "N"], ["S", "E"]],
         warunkowe=[["N", "E"], ["S", "W"]],
         zielone_s=30),
    Faza("Faza 2: W-E",
         zielone=[["E", "W"], ["E", "N"], ["W", "E"], ["W", "S"]],
         warunkowe=[["E", "S"], ["W", "N"]],
         zielone_s=20),
])

# bledne specjalnie dla testu, N i E jednoczesnie lewo na zielonym pelnym
PROGRAM_ZLY = ProgramSwiatel("C", fazy=[
    Faza("Faza 1", zielone=[["N", "S"], ["E", "W"], ["S", "W"]], zielone_s=30,
         wszystkie_czerwone_s=0),
    Faza("Faza 2", zielone=[["W", "E"]], zielone_s=3, zolte_s=2),
])


def pokaz(program: ProgramSwiatel, tytul: str) -> Path | None:
    print(f"\n{'=' * 70}\n{tytul}\n{'=' * 70}")
    wynik = eksportuj_z_fazami(skrzyzowanie_4_wloty(), [program], KATALOG)
    for o in wynik.ostrzezenia:
        print("eksport:", o)
    skrz = wynik.skrzyzowania["C"]

    print(f"\nPołączenia na skrzyżowaniu {skrz.wezel} (typ SUMO: {skrz.typ}):")
    for p in skrz.polaczenia:
        print(f"  [{p.indeks:2}] {p.wlot}→{p.wylot:<3} {p.kierunek_opis:<9} pas {p.pas}")

    print("\nProgram SUMO (jeden znak na połączenie):")
    for s in zbuduj_stany(program, skrz):
        print(f"  {s.stan}  {s.czas_s:>4g} s  {s.nazwa}")
    print(f"  cykl: {czas_cyklu(program, skrz):g} s")

    print("\nCzasy w cyklu [s]:      zielone  żółte  czerwone  czerw.+żółte")
    for (a, b), c in czasy_relacji(program, skrz).items():
        print(f"  {a}→{b:<3} {skrz.kierunek_relacji((a, b)):<10}"
              f"{c['zielone']:>9g}{c['zolte']:>7g}{c['czerwone']:>10g}{c['czerwone_zolte']:>14g}")

    print("\nWeryfikacja:")
    for p in wynik.problemy or ["  brak problemów"]:
        print(" ", p)
    print("\nSieć:", wynik.siec or "NIE ZAPISANA (program ma błędy)")
    return wynik.siec

def wloty_wyloty(projekt, wezel="C"):
    # krawędzie wjeżdżające do węzła i wyjeżdżające z niego, z kierunku każdej drogi
    wloty, wyloty = {}, {}
    for d in projekt.drogi:
        if d.do == wezel:
            if d.pasy_tam:
                wloty[d.id] = id_krawedzi(d.id, True)
            if d.pasy_powrot:
                wyloty[d.id] = id_krawedzi(d.id, False)
        elif d.od == wezel:
            if d.pasy_tam:
                wyloty[d.id] = id_krawedzi(d.id, True)
            if d.pasy_powrot:
                wloty[d.id] = id_krawedzi(d.id, False)
    return wloty, wyloty


def zapisz_trasy(sciezka: Path) -> Path:
    wloty, wyloty = wloty_wyloty(skrzyzowanie_4_wloty())
    routes = ET.Element("routes")
    for skad, e_z in wloty.items():
        for dokad, e_do in wyloty.items():
            if skad != dokad:
                ET.SubElement(routes, "flow", {"id": f"{skad}{dokad}", "from": e_z, "to": e_do,
                                               "begin": "0", "end": "900", "vehsPerHour": "120"})
    ET.indent(routes)
    ET.ElementTree(routes).write(sciezka, encoding="utf-8", xml_declaration=True)
    return sciezka


def uruchom_sumo(siec: Path, gui: bool) -> None:
    trasy = zapisz_trasy(KATALOG / "trasy.rou.xml")
    polecenie = [znajdz_program("sumo-gui" if gui else "sumo"), "-n", str(siec), "-r", str(trasy),
                 "--end", "900", "--no-step-log", "--duration-log.statistics",
                 "--collision.check-junctions", "true", "--collision.action", "warn"]
    print("\nSymulacja 15 min w SUMO:")
    wynik = subprocess.run(polecenie, capture_output=True, text=True)
    for linia in (wynik.stdout + wynik.stderr).splitlines():
        if any(s in linia for s in ("Inserted", "Teleports", "Collisions", "WaitingTime",
                                     "TimeLoss", "Warning", "Error")):
            print(" ", linia.strip())


if __name__ == "__main__":
    KATALOG.mkdir(exist_ok=True)
    siec = pokaz(PROGRAM_DOBRY, "Program poprawny: dwie fazy z lewoskrętem warunkowym")
    pokaz(PROGRAM_ZLY, "Program celowo błędny (dla pokazania weryfikacji)")
    if siec and ("--sumo" in sys.argv or "--gui" in sys.argv):
        # pokaz() z programem złym nadpisał pliki to dobry jeszcze raz zeby poprawic
        siec = eksportuj_z_fazami(skrzyzowanie_4_wloty(), [PROGRAM_DOBRY], KATALOG).siec
        uruchom_sumo(siec, gui="--gui" in sys.argv)
