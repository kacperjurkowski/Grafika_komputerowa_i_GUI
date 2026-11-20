"""Kontrakty między GUI a modułami Junctio.

GUI łączy się z trzema modułami wyłącznie
przez interfejsy zdefiniowane w tym pliku:

    GeometryPort – geometria: sieć węzłów i dróg, kształty do narysowania, edycja, pliki projektu,
    EnginePort   – silnik: symulacja ruchu, pojazdy, statystyki,
    ControlPort  – sterowanie skrzyżowaniem: fazy świateł i stany sygnalizatorów.

Zasady wspólne dla wszystkich modułów:
 1. Współrzędne są w metrach, oś Y skierowana w górę. Kąty w radianach
    (0 = kierunek osi X, dodatnie przeciwnie do ruchu wskazówek zegara).
 2. Obiekty zwracane przez moduły (Scene, VehicleView itd.) są migawkami tylko do odczytu.
    GUI nigdy ich nie zmienia – każdą zmianę zgłasza metodą portu.
 3. Po każdej zmianie danych moduł wywołuje odpowiedni Observable.emit(). Można to robić
    z dowolnego wątku, GUI samo przeniesie wywołanie do swojego wątku.
 4. Błąd, o którym ma się dowiedzieć użytkownik, to BackendError z komunikatem po polsku (lub wybranym języku, do dopracowania).
    GUI pokaże go w oknie dialogowym.
 5. Moduł, który jeszcze nie istnieje, jest zastępowany atrapą z available = False (stubs.py).
    GUI wyłącza wtedy związane z nim funkcje i pokazuje informację.
 6. Czas symulacji napędza GUI: co ok. 33 ms wywołuje EnginePort.advance(rzeczywisty_dt),
    dopóki status().running == True.
"""

# import z pakietów standardowych

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

# importy modeli danych

Point = Tuple[float, float]  # (x, y) w metrach

NODE = "wezel"   # ElementRef.kind dla węzła
ROAD = "droga"   # ElementRef.kind dla drogi

""" Obsługa błędów backendu """

class BackendError(Exception):
    """Błąd zgłaszany przez moduły; treść trafia do użytkownika."""

""" Obsługa zdarzeń backendu """

class Observable:
    """Zdarzenie bez argumentów: moduł woła emit(), GUI podpisuje się przez connect()."""

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def disconnect(self, callback):
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def emit(self):
        for cb in list(self._callbacks):
            cb()


""" Geometria: dane przekazywane do GUI """

@dataclass(frozen=True)
class ElementRef:
    """Wskazanie elementu sieci. Pusty (NONE) oznacza 'nic'."""
    kind: str = ""   # NODE | ROAD | ""
    id: str = ""

    def __bool__(self):
        return bool(self.kind and self.id)


NONE = ElementRef()

""" Węzeł przekazywany do GUI """

@dataclass
class NodeView:
    id: str
    x: float
    y: float
    kind: str = "brak"  # "brak", "swiatla", "pierwszenstwo", "stop", "stop_wszystkie" (GUI zna kolory tych kluczy)
    label: str = ""     # tekst na liście elementów; puste = GUI złoży go z id i kind

""" Droga przekazywana do GUI """

@dataclass
class RoadView:
    id: str
    from_id: str
    to_id: str
    label: str = ""
    is_main: bool = False                                        # droga z pierwszeństwem (ciemniejsza)
    center_line: list = field(default_factory=list)              # [Point, ...] oś drogi; rysowana, gdy brak surface
    surface: list = field(default_factory=list)                  # [Point, ...] zamknięty obrys jezdni
    lane_lines: list = field(default_factory=list)               # [[Point, ...], ...] linie pasów (przerywane)

""" Cała scena do narysowania w edytorze i w symulacji."""

@dataclass
class Scene:
    nodes: list = field(default_factory=list)    # [NodeView]
    roads: list = field(default_factory=list)    # [RoadView]
    areas: list = field(default_factory=list)    # [[Point, ...], ...] powierzchnie skrzyżowań (wielokąty)
    bounds: Optional[Tuple[float, float, float, float]] = None  # (xmin, ymin, xmax, ymax); None = GUI policzy

"""Opis jednego pola listy właściwości; GUI buduje listę z takich pól."""

@dataclass
class PropertyField:
    key: str
    label: str
    kind: str                       # "text" | "int" | "float" | "bool" | "choice"
    value: object
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 1
    suffix: str = ""
    choices: list = field(default_factory=list)  # [(wartość, podpis), ...] dla kind == "choice"
    readonly: bool = False

""" Informacje o dokumencie do wyświetlenia """

@dataclass
class DocumentInfo:
    name: str = "bez_nazwy"
    path: Optional[str] = None
    dirty: bool = False
    saved_at: Optional[datetime] = None


""" Silnik: dane przekazywane do GUI """

""" Dane o samochodzie do wyświetlenia """

@dataclass
class VehicleView:
    id: str
    x: float
    y: float
    heading: float = 0.0            # kierunek jazdy [rad]
    length: float = 4.5             # [m]
    width: float = 1.8              # [m]
    kind: str = "car"               # "car" | "truck" | "bus" (wpływa tylko na kolor)
    color: Optional[str] = None     # opcjonalny kolor "#RRGGBB" narzucony przez silnik

"""Dane o symulacji do wyświetlenia """
@dataclass
class SimStatus:
    time_s: float = 0.0
    running: bool = False
    speed: float = 1.0              # mnożnik czasu symulacji względem rzeczywistego
    vehicles: int = 0

""" Dane o serii wybranej wartości do wyświetlenia """
@dataclass
class Series:
    name: str
    unit: str = ""
    points: list = field(default_factory=list)   # [(t [s], wartość), ...]

""" Statystyki do wyświetlenia """
@dataclass
class StatsSnapshot:
    summary: list = field(default_factory=list)  # [(nazwa wskaźnika, tekst wartości), ...]
    series: list = field(default_factory=list)   # [Series]


""" Sterowanie: dane przekazywane do GUI """

""" Dane o ruchu do wyświetlenia """
@dataclass
class MovementView:
    id: str
    label: str

""" Dane o ruchu w danej fazie świateł do wyświetlenia """
@dataclass
class PhaseView:
    id: str
    name: str
    duration_s: float
    movements: list = field(default_factory=list)  # id ruchów, które mają w tej fazie zielone

""" Dane o sygnalizacji do wyświetlenia """
@dataclass
class SignalHeadView:
    id: str
    x: float
    y: float
    state: str = "off"              # "red" | "yellow" | "green" | "off"


# ───────────────────────────── Porty (interfejsy modułów) ─────────────────────────────

""" Uniwersalny port dla aktualizacji danych w GUI przy zmianie danych modułu """

class Port(ABC):
    available = True  # atrapy ustawiają False

    def __init__(self):
        self.changed = Observable()  # zmieniły się dane modułu → GUI odświeży widoki

""" Port dla geometrii do przesyłu danych do GUI """

class GeometryPort(Port):
    """Geometria: sieć węzłów i dróg, jej kształt do narysowania, edycja oraz pliki projektu."""

    file_filter = "Projekt Junctio (*.json)"  # filtr okien 'Otwórz' / 'Zapisz jako'
    default_suffix = ".json"

    def __init__(self):
        super().__init__()
        self.loaded = Observable()  # podmieniono cały projekt (nowy / otwarty); emit() po new_project i open_project

    # --- projekt (dokument) ---
    @abstractmethod
    def new_project(self):
        """Tworzy pusty projekt i woła loaded.emit()."""

    @abstractmethod
    def open_project(self, path: str):
        """Wczytuje projekt z pliku, woła loaded.emit(). Błąd pliku → BackendError."""

    @abstractmethod
    def save_project(self, path: str):
        """Zapisuje projekt do pliku, ustawia dirty = False i woła changed.emit()."""

    @abstractmethod
    def document(self) -> DocumentInfo:
        """Nazwa, ścieżka, flaga niezapisanych zmian i czas ostatniego zapisu."""

    # --- odczyt geometrii ---
    @abstractmethod
    def scene(self) -> Scene:
        """Aktualna migawka sieci do narysowania (współrzędne świata, w metrach)."""

    @abstractmethod
    def hit_test(self, x: float, y: float, tolerance: float) -> ElementRef:
        """Element pod punktem (x, y) [m] z tolerancją [m]; węzły mają pierwszeństwo przed drogami."""

    def snap(self, x: float, y: float) -> Point:
        """Przyciąganie punktu (siatka, węzły, ...). Domyślnie bez przyciągania."""
        return (x, y)

    # --- edycja (po każdej zmianie: changed.emit(), dirty = True) ---
    @abstractmethod
    def add_node(self, x: float, y: float) -> ElementRef:
        """Dodaje węzeł i zwraca jego referencję."""

    @abstractmethod
    def move_node(self, node_id: str, x: float, y: float, final: bool):
        """Przesuwa węzeł. final=False w trakcie przeciągania, final=True po puszczeniu przycisku myszy."""

    @abstractmethod
    def add_road(self, from_id: str, to_id: str) -> ElementRef:
        """Dodaje drogę między węzłami. Niedozwolone połączenie → BackendError."""

    @abstractmethod
    def delete(self, ref: ElementRef):
        """Usuwa element (usunięcie węzła usuwa też jego drogi)."""

    @abstractmethod
    def properties(self, ref: ElementRef) -> list:
        """Lista PropertyField opisująca edytowalne właściwości elementu."""

    @abstractmethod
    def set_property(self, ref: ElementRef, key: str, value):
        """Ustawia właściwość o kluczu PropertyField.key. Niedozwolona wartość → BackendError."""

""" Port dla silnika do przesyłu danych do GUI """

class EnginePort(Port):
    """Silnik symulacji ruchu."""

    def __init__(self):
        super().__init__()
        self.status_changed = Observable()  # start / pauza / reset / zmiana prędkości

    @abstractmethod
    def check_ready(self) -> list:
        """Lista problemów uniemożliwiających start (po polsku). Pusta lista = można startować."""

    @abstractmethod
    def start(self): ...

    @abstractmethod
    def pause(self): ...

    @abstractmethod
    def reset(self):
        """Wraca do czasu 0 i zatrzymuje symulację."""

    @abstractmethod
    def step(self):
        """Jeden krok symulacji (gdy zatrzymana)."""

    @abstractmethod
    def set_speed(self, factor: float):
        """Mnożnik czasu symulacji (GUI oferuje 0.5, 1, 2, 5, 10)."""

    @abstractmethod
    def advance(self, real_dt: float):
        """Wołane przez GUI co ok. 33 ms, gdy status().running; real_dt w sekundach rzeczywistych."""

    @abstractmethod
    def status(self) -> SimStatus: ...

    @abstractmethod
    def vehicles(self) -> list:
        """[VehicleView] – pojazdy do narysowania w bieżącym momencie."""

    @abstractmethod
    def statistics(self) -> StatsSnapshot: ...

""" Port dla sterowania do przesyłu danych do GUI """

class ControlPort(Port):
    """Sterowanie skrzyżowaniem: fazy świateł i stany sygnalizatorów."""

    @abstractmethod
    def signalized_nodes(self) -> list:
        """[(id węzła, podpis)] – skrzyżowania z sygnalizacją świetlną."""

    @abstractmethod
    def movements(self, node_id: str) -> list:
        """[MovementView] – ruchy, którym można przypisać zielone w fazach."""

    @abstractmethod
    def phases(self, node_id: str) -> list:
        """[PhaseView] w kolejności wykonywania."""

    @abstractmethod
    def add_phase(self, node_id: str):
        """Dodaje fazę na końcu cyklu i woła changed.emit()."""

    @abstractmethod
    def remove_phase(self, node_id: str, phase_id: str): ...

    @abstractmethod
    def update_phase(self, node_id: str, phase_id: str, name=None, duration_s=None, movements=None):
        """Zmienia tylko te pola, które nie są None. Niedozwolona wartość → BackendError."""

    @abstractmethod
    def signal_heads(self) -> list:
        """[SignalHeadView] – sygnalizatory ze stanem w bieżącym momencie symulacji."""

""" Klasa backendu i moduły składowe """
@dataclass
class Backend:
    geometry: GeometryPort
    engine: EnginePort
    control: ControlPort
