"""Warstwa pośrednia między widgetami GUI a modułami (geometria, silnik, sterowanie).

Session przechowuje tylko to, co GUI potrzebuje do rysowania: ostatnie migawki z modułów
oraz bieżące zaznaczenie. Nie zawiera żadnej logiki skrzyżowania.
"""
import time
from datetime                   import datetime

from PySide6.QtCore             import QObject, QTimer, Signal

from contracts  import (NODE, NONE, ROAD, BackendError, DocumentInfo, ElementRef, Scene, SimStatus,
                       StatsSnapshot)

_FAIL = object()


"""     Pośrednik między widgetami a modułami. 
        Trzyma ostatnie migawki (scena, dokument, pojazdy, sygnalizatory), zaznaczenie i zegar symulacji. 
        Zamienia zdarzenia modułów na sygnały Qt oraz błędy modułów na sygnał error. 
"""
class Session(QObject):
    scene_changed       = Signal()          # nowa migawka geometrii
    document_changed    = Signal()          # zmieniła się nazwa / ścieżka / flaga zapisu
    selection_changed   = Signal()
    loaded              = Signal()          # podmieniono cały projekt
    sim_changed         = Signal()          # status, pojazdy lub sygnalizatory
    phases_changed      = Signal()          # zmiana faz świateł
    error               = Signal(str)       # komunikat dla użytkownika

    # mosty zdarzeń modułów → wątek GUI (emit z dowolnego wątku jest bezpieczny)
    _geo_changed, _geo_loaded, _eng_changed, _ctl_changed = Signal(), Signal(), Signal(), Signal()

    """ Podpina zdarzenia modułów do sygnałów Qt, uruchamia zegar (33 ms) i pobiera pierwsze migawki. """

    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.g, self.e, self.c = backend.geometry, backend.engine, backend.control
        self.scene, self.doc, self.selection = Scene(), DocumentInfo(), NONE
        self.status, self.vehicles, self.heads = SimStatus(), [], []

        self.g.changed.connect(self._geo_changed.emit)
        self.g.loaded.connect(self._geo_loaded.emit)
        self.e.status_changed.connect(self._eng_changed.emit)
        self.c.changed.connect(self._ctl_changed.emit)
        self._geo_changed.connect(self.reload_scene)
        self._geo_loaded.connect(self._on_loaded)
        self._eng_changed.connect(self.refresh_sim)
        self._ctl_changed.connect(self.phases_changed)

        self._last = time.perf_counter()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start(33)
        self.reload_scene()
        self.refresh_sim()

    """ Wywołuje metodę modułu; BackendError i NotImplementedError zamienia na sygnał error i zwraca default. """

    def _call(self, fn, default, *args):
        try:
            return fn(*args)
        except BackendError as e:
            self.error.emit(str(e))
        except NotImplementedError:
            self.error.emit("Ta funkcja nie jest jeszcze zaimplementowana.")
        return default

    """ Wywołuje komendę; zwraca True, jeśli się powiodła. """

    def _do(self, fn, *args):
        return self._call(fn, _FAIL, *args) is not _FAIL

    """ Pobiera scenę i dane dokumentu z geometrii, usuwa nieistniejące zaznaczenie i powiadamia widgety. """

    def reload_scene(self):
        self.scene = self._call(self.g.scene, self.scene)
        self.doc = self._call(self.g.document, self.doc)
        refs = {ElementRef(NODE, n.id) for n in self.scene.nodes} | {ElementRef(ROAD, r.id) for r in self.scene.roads}
        if self.selection and self.selection not in refs:
            self.selection = NONE
            self.selection_changed.emit()
        self.scene_changed.emit()
        self.document_changed.emit()

    """ Reakcja na podmianę projektu: czyści zaznaczenie, odświeża scenę i zleca dopasowanie widoku. """

    def _on_loaded(self):
        self.selection = NONE
        self.reload_scene()
        self.selection_changed.emit()
        self.loaded.emit()

    """Tekst statusu pliku do karty w panelu bocznym, np. „Zapisano 2 min temu”."""
    
    def doc_status(self):
        d = self.doc
        if d.dirty:
            return "Niezapisane zmiany"
        if not d.saved_at:
            return "Zapisano" if d.path else "Nowy projekt"
        m = int((datetime.now() - d.saved_at).total_seconds() // 60)
        if m < 1:
            return "Zapisano przed chwilą"
        return f"Zapisano {m} min temu" if m < 60 else f"Zapisano {d.saved_at:%d.%m.%Y %H:%M}"

    """ Przykładowe metody wywołujące funkcje modułów """

    # operacje na plikach

    def new_project(self):
        return self._do(self.g.new_project)

    def open_project(self, path):
        return self._do(self.g.open_project, path)

    def save_project(self, path):
        return self._do(self.g.save_project, path)

    # operacje geometryczne

    def select(self, ref):
        if ref != self.selection:
            self.selection = ref
            self.selection_changed.emit()

    def hit(self, x, y, tolerance):
        return self._call(self.g.hit_test, NONE, x, y, tolerance)

    def snap(self, x, y):
        return self._call(self.g.snap, (x, y), x, y)

    def add_node(self, x, y):
        ref = self._call(self.g.add_node, NONE, x, y)
        if ref:
            self.select(ref)

    def move_node(self, node_id, x, y, final):
        self._do(self.g.move_node, node_id, x, y, final)

    def add_road(self, from_id, to_id):
        ref = self._call(self.g.add_road, NONE, from_id, to_id)
        if ref:
            self.select(ref)

    def delete_selected(self):
        if self.selection and self._do(self.g.delete, self.selection):
            self.select(NONE)

    def properties(self):
        return self._call(self.g.properties, [], self.selection) if self.selection else []

    def set_property(self, key, value):
        if self.selection:
            self._do(self.g.set_property, self.selection, key, value)

    # operacje symulacyjne

    def refresh_sim(self):
        self.status = self._call(self.e.status, self.status)
        self.vehicles = self._call(self.e.vehicles, [])
        self.heads = self._call(self.c.signal_heads, [])
        self.sim_changed.emit()

    def _cmd(self, fn, *args):
        self._do(fn, *args)
        self.refresh_sim()

    def start(self):
        problems = self._call(self.e.check_ready, [])
        if problems:
            self.error.emit("Nie można uruchomić symulacji:\n• " + "\n• ".join(problems))
            return
        self._cmd(self.e.start)

    def pause(self):
        self._cmd(self.e.pause)

    def reset(self):
        self._cmd(self.e.reset)

    def step(self):
        self._cmd(self.e.step)

    def set_speed(self, factor):
        self._cmd(self.e.set_speed, factor)

    def statistics(self):
        return self._call(self.e.statistics, StatsSnapshot())

    def _on_timer(self):
        now = time.perf_counter()
        dt, self._last = min(now - self._last, 0.25), now
        if self.status.running:
            self._do(self.e.advance, dt)
            self.refresh_sim()

    # operacje sterowania
    
    def signalized_nodes(self):
        return self._call(self.c.signalized_nodes, [])

    def movements(self, node_id):
        return self._call(self.c.movements, [], node_id)

    def phases(self, node_id):
        return self._call(self.c.phases, [], node_id)

    def add_phase(self, node_id):
        self._do(self.c.add_phase, node_id)

    def remove_phase(self, node_id, phase_id):
        self._do(self.c.remove_phase, node_id, phase_id)

    def update_phase(self, node_id, phase_id, **fields):
        return self._do(lambda: self.c.update_phase(node_id, phase_id, **fields))
