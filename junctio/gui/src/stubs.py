""" Atrapy modułów: pozwalają uruchomić samo GUI, zanim powstaną prawdziwe implementacje.
    Służą też jako szablon – każdy moduł musi zaimplementować te same metody.
"""

# importy portów dla modułów
from contracts import (NONE, BackendError, ControlPort, DocumentInfo, EnginePort, GeometryPort, Scene,
                       SimStatus, StatsSnapshot)


def _missing(name):
    return BackendError(f"Moduł „{name}” nie jest jeszcze podłączony.")

""" Atrapa modułu geometrii """

class NullGeometry(GeometryPort):
    available = False

    def new_project(self): pass
    def open_project(self, path): raise _missing("geometria")
    def save_project(self, path): raise _missing("geometria")
    def document(self): return DocumentInfo()
    def scene(self): return Scene()
    def hit_test(self, x, y, tolerance): return NONE
    def add_node(self, x, y): return NONE
    def move_node(self, node_id, x, y, final): pass
    def add_road(self, from_id, to_id): return NONE
    def delete(self, ref): pass
    def properties(self, ref): return []
    def set_property(self, ref, key, value): pass

""" Atrapa modułu silnika """

class NullEngine(EnginePort):
    available = False

    def check_ready(self): return ["Moduł „silnik” nie jest jeszcze podłączony."]
    def start(self): pass
    def pause(self): pass
    def reset(self): pass
    def step(self): pass
    def set_speed(self, factor): pass
    def advance(self, real_dt): pass
    def status(self): return SimStatus()
    def vehicles(self): return []
    def statistics(self): return StatsSnapshot()

""" Atrapa modułu sterowania """

class NullControl(ControlPort):
    available = False

    def signalized_nodes(self): return []
    def movements(self, node_id): return []
    def phases(self, node_id): return []
    def add_phase(self, node_id): pass
    def remove_phase(self, node_id, phase_id): pass
    def update_phase(self, node_id, phase_id, name=None, duration_s=None, movements=None): pass
    def signal_heads(self): return []
