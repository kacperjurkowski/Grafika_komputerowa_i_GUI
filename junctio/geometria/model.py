from dataclasses import dataclass, field
from typing import List

@dataclass
class Wezel:
    id: str
    x: float  # metry, oś Y w górę
    y: float
    rodzaj: str = "brak"  # "brak", "swiatla", "pierwszenstwo", "stop", "stop_wszystkie"

@dataclass
class Droga:
    id: str
    od: str
    do: str
    ksztalt: list = field(default_factory=list)
    pasy_tam: int = 1
    pasy_powrot: int = 1
    predkosc_kmh: int = 50
    glowna: bool = False

@dataclass
class Projekt:
    version: int = 1
    wezly: List[Wezel] = field(default_factory=list)
    drogi: List[Droga] = field(default_factory=list)