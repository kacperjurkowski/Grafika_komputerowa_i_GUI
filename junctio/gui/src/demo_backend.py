"""Backend DEMONSTRACYJNY – wyłącznie do oglądania i testowania GUI (python main.py --demo).

To nie jest część kontraktu ani docelowa implementacja: prosta geometria w pamięci, symulacja
pojazdów jadących po liniach prostych i dwufazowa sygnalizacja z danymi na pokaz.
"""

#importy z pakietów standardowych

import json
import math
from datetime import datetime
from pathlib import Path

# importy portów modułów i modeli danych

from contracts import (NODE, NONE, ROAD, Backend, BackendError, ControlPort, DocumentInfo, ElementRef,
                       EnginePort, GeometryPort, MovementView, NodeView, PhaseView, PropertyField, RoadView,
                       Scene, Series, SignalHeadView, SimStatus, StatsSnapshot, VehicleView)

""" Dane testowe do geometrii, silnika i sterowania."""

LANE = 3.5
KINDS = [("brak", "brak"), ("swiatla", "światła"), ("pierwszenstwo", "pierwszeństwo"),
         ("stop", "stop"), ("stop_wszystkie", "stop (wszystkie)")]

"""Odległość punktu (px, py) od odcinka (ax, ay)–(bx, by)."""

def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

"""Pierwszy wolny identyfikator z danym prefiksem (np. W1, W2, ...)."""

def _new_id(prefix, used):
    n = 1
    while f"{prefix}{n}" in used:
        n += 1
    return f"{prefix}{n}"

"""Geometria w pamięci: słowniki węzłów i dróg, jezdnie jako prostokąty, zapis do prostego JSON."""

class DemoGeometry(GeometryPort):
    file_filter = "Projekt demo (*.json)"

    """Tworzy przykładowe skrzyżowanie z czterema wlotami."""

    def __init__(self):
        super().__init__()
        self.path, self.dirty, self.saved_at = None, False, None
        self._seed()

    def _seed(self):
        self.nodes = {"C": dict(x=0.0, y=0.0, kind="swiatla"), "N": dict(x=0.0, y=100.0, kind="brak"),
                      "E": dict(x=100.0, y=0.0, kind="brak"), "S": dict(x=0.0, y=-100.0, kind="brak"),
                      "W": dict(x=-100.0, y=0.0, kind="brak")}
        self.roads = {f"D{i}": dict(od=o, do="C", tam=1, powrot=1, v=50, main=m)
                      for i, (o, m) in enumerate((("N", True), ("S", True), ("E", False), ("W", False)), 1)}

    def _touch(self):
        self.dirty = True
        self.changed.emit()

    # --- dokument ---
    def new_project(self):
        self.nodes, self.roads = {}, {}
        self.path, self.dirty, self.saved_at = None, False, None
        self.loaded.emit()

    def open_project(self, path):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.nodes, self.roads = data["nodes"], data["roads"]
        except (OSError, ValueError, KeyError) as e:
            raise BackendError(f"Nie można otworzyć pliku: {e}")
        self.path, self.dirty = str(path), False
        self.saved_at = datetime.fromtimestamp(Path(path).stat().st_mtime)
        self.loaded.emit()

    def save_project(self, path):
        try:
            Path(path).write_text(json.dumps({"nodes": self.nodes, "roads": self.roads}, indent=2), encoding="utf-8")
        except OSError as e:
            raise BackendError(f"Nie można zapisać pliku: {e}")
        self.path, self.dirty, self.saved_at = str(path), False, datetime.now()
        self.changed.emit()

    def document(self):
        return DocumentInfo(name=Path(self.path).stem if self.path else "bez_nazwy", path=self.path,
                            dirty=self.dirty, saved_at=self.saved_at)

    """Buduje scenę: obrysy jezdni (prostokąty), linie pasów i powierzchnie skrzyżowań ze światłami."""

    def scene(self):
        nodes = [NodeView(i, n["x"], n["y"], n["kind"], f"{i}   {n['kind']}") for i, n in self.nodes.items()]
        roads = []
        for i, r in self.roads.items():
            a, b = self.nodes[r["od"]], self.nodes[r["do"]]
            pa, pb = (a["x"], a["y"]), (b["x"], b["y"])
            rv = RoadView(i, r["od"], r["do"], f"{i}   {r['od']} → {r['do']}", r["main"], center_line=[pa, pb])
            length = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
            if length > 0:
                h = (r["tam"] + r["powrot"]) * LANE / 2
                nx, ny = -(pb[1] - pa[1]) / length * h, (pb[0] - pa[0]) / length * h
                rv.surface = [(pa[0] + nx, pa[1] + ny), (pb[0] + nx, pb[1] + ny),
                              (pb[0] - nx, pb[1] - ny), (pa[0] - nx, pa[1] - ny)]
                if r["powrot"] > 0:
                    rv.lane_lines = [[pa, pb]]
            roads.append(rv)
        areas = [[(n["x"] - 7, n["y"] - 7), (n["x"] + 7, n["y"] - 7), (n["x"] + 7, n["y"] + 7), (n["x"] - 7, n["y"] + 7)]
                 for n in self.nodes.values() if n["kind"] == "swiatla"]
        return Scene(nodes, roads, areas)

    def hit_test(self, x, y, tolerance):
        for i, n in reversed(list(self.nodes.items())):
            if math.hypot(n["x"] - x, n["y"] - y) <= tolerance:
                return ElementRef(NODE, i)
        for i, r in reversed(list(self.roads.items())):
            a, b = self.nodes[r["od"]], self.nodes[r["do"]]
            if _seg_dist(x, y, a["x"], a["y"], b["x"], b["y"]) <= max(tolerance, (r["tam"] + r["powrot"]) * LANE / 2):
                return ElementRef(ROAD, i)
        return NONE

    def snap(self, x, y):
        return (float(round(x)), float(round(y)))

    # --- edycja ---
    def add_node(self, x, y):
        i = _new_id("W", self.nodes)
        self.nodes[i] = dict(x=x, y=y, kind="brak")
        self._touch()
        return ElementRef(NODE, i)

    def move_node(self, node_id, x, y, final):
        if node_id in self.nodes:
            self.nodes[node_id].update(x=x, y=y)
            self._touch()

    def add_road(self, from_id, to_id):
        if any({r["od"], r["do"]} == {from_id, to_id} for r in self.roads.values()):
            raise BackendError("Między tymi węzłami istnieje już droga.")
        i = _new_id("D", self.roads)
        self.roads[i] = dict(od=from_id, do=to_id, tam=1, powrot=1, v=50, main=False)
        self._touch()
        return ElementRef(ROAD, i)

    def delete(self, ref):
        if ref.kind == NODE:
            self.nodes.pop(ref.id, None)
            self.roads = {i: r for i, r in self.roads.items() if ref.id not in (r["od"], r["do"])}
        elif ref.kind == ROAD:
            self.roads.pop(ref.id, None)
        self._touch()

    def properties(self, ref):
        if ref.kind == NODE and ref.id in self.nodes:
            n = self.nodes[ref.id]
            return [PropertyField("id", "ID", "text", ref.id),
                    PropertyField("x", "X", "float", n["x"], -10000, 10000, 1, 1, " m"),
                    PropertyField("y", "Y", "float", n["y"], -10000, 10000, 1, 1, " m"),
                    PropertyField("kind", "Rodzaj", "choice", n["kind"], choices=KINDS)]
        if ref.kind == ROAD and ref.id in self.roads:
            r = self.roads[ref.id]
            return [PropertyField("id", "ID", "text", ref.id),
                    PropertyField("link", "Od → do", "text", f"{r['od']} → {r['do']}"),
                    PropertyField("tam", "Pasy od → do", "int", r["tam"], 1, 8),
                    PropertyField("powrot", "Pasy do → od", "int", r["powrot"], 0, 8),
                    PropertyField("v", "Prędkość", "int", r["v"], 10, 140, 10, suffix=" km/h"),
                    PropertyField("main", "Droga z pierwszeństwem", "bool", r["main"])]
        return []

    def set_property(self, ref, key, value):
        item = self.nodes.get(ref.id) if ref.kind == NODE else self.roads.get(ref.id)
        if item is not None and key in item:
            item[key] = value
            self._touch()

"""Silnik na pokaz: po trzy pojazdy jadące równym tempem wzdłuż każdej drogi, dane statystyk wymyślone."""

class DemoEngine(EnginePort):
    def __init__(self, geometry):
        super().__init__()
        self.g, self.t, self.running, self.speed = geometry, 0.0, False, 1.0
        self._hist, self._next = [], 0.0

    def check_ready(self):
        return [] if self.g.roads else ["Projekt nie zawiera żadnych dróg."]

    def start(self):
        self.running = True
        self.status_changed.emit()

    def pause(self):
        self.running = False
        self.status_changed.emit()

    def reset(self):
        self.t, self.running, self._hist, self._next = 0.0, False, [], 0.0
        self.status_changed.emit()

    def step(self):
        self._tick(0.5)
        self.status_changed.emit()

    def set_speed(self, factor):
        self.speed = factor
        self.status_changed.emit()

    def advance(self, real_dt):
        if self.running:
            self._tick(real_dt * self.speed)

    def _tick(self, dt):
        self.t += dt
        while self.t >= self._next:
            self._hist.append((self._next, 36 + 6 * math.sin(self._next / 8)))  # dane na pokaz
            self._next += 1.0

    def status(self):
        return SimStatus(self.t, self.running, self.speed, len(self.vehicles()))

    def vehicles(self):
        out = []
        for i, r in self.g.roads.items():
            a, b = self.g.nodes[r["od"]], self.g.nodes[r["do"]]
            length = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
            if length == 0:
                continue
            ux, uy = (b["x"] - a["x"]) / length, (b["y"] - a["y"]) / length
            off = (r["tam"] + r["powrot"]) * LANE / 4
            for j in range(3):
                u = (self.t * 10 / length + j / 3) % 1.0
                out.append(VehicleView(f"{i}-{j}", a["x"] + ux * length * u + uy * off,
                                       a["y"] + uy * length * u - ux * off, math.atan2(uy, ux)))
        return out

    def statistics(self):
        return StatsSnapshot([("Czas symulacji", f"{self.t:.1f} s"), ("Pojazdy w obiegu", str(len(self.vehicles()))),
                              ("Średnia prędkość", "36 km/h (dane na pokaz)")],
                             [Series("Średnia prędkość", "km/h", list(self._hist))])

"""Sterowanie na pokaz: dwie fazy dla każdego skrzyżowania ze światłami, stany z czasu silnika."""

class DemoControl(ControlPort):
    def __init__(self, geometry, engine):
        super().__init__()
        self.g, self.e, self._ph = geometry, engine, {}

    def _list(self, node_id):
        if node_id not in self._ph:
            inc = [(i, r) for i, r in self.g.roads.items() if r["do"] == node_id]
            self._ph[node_id] = [dict(id="P1", name="Droga główna", dur=30.0, mov=[i for i, r in inc if r["main"]]),
                                 dict(id="P2", name="Droga poprzeczna", dur=20.0, mov=[i for i, r in inc if not r["main"]])]
        return self._ph[node_id]

    def signalized_nodes(self):
        return [(i, f"Węzeł {i}") for i, n in self.g.nodes.items() if n["kind"] == "swiatla"]

    def movements(self, node_id):
        return [MovementView(i, f"Wlot z {r['od']}") for i, r in self.g.roads.items() if r["do"] == node_id]

    def phases(self, node_id):
        return [PhaseView(p["id"], p["name"], p["dur"], list(p["mov"])) for p in self._list(node_id)]

    def add_phase(self, node_id):
        lst = self._list(node_id)
        pid = _new_id("P", {p["id"] for p in lst})
        lst.append(dict(id=pid, name=f"Faza {len(lst) + 1}", dur=20.0, mov=[]))
        self.changed.emit()

    def remove_phase(self, node_id, phase_id):
        self._ph[node_id] = [p for p in self._list(node_id) if p["id"] != phase_id]
        self.changed.emit()

    def update_phase(self, node_id, phase_id, name=None, duration_s=None, movements=None):
        for p in self._list(node_id):
            if p["id"] == phase_id:
                if name is not None:
                    p["name"] = name
                if duration_s is not None:
                    p["dur"] = duration_s
                if movements is not None:
                    p["mov"] = list(movements)
        self.changed.emit()

    def signal_heads(self):
        out = []
        for nid, _ in self.signalized_nodes():
            phases = self._list(nid)
            cycle = sum(p["dur"] for p in phases) or 1.0
            t, acc, cur, left = self.e.t % cycle, 0.0, None, 0.0
            for p in phases:
                if t < acc + p["dur"]:
                    cur, left = p, acc + p["dur"] - t
                    break
                acc += p["dur"]
            n = self.g.nodes[nid]
            for m in self.movements(nid):
                a = self.g.nodes[self.g.roads[m.id]["od"]]
                dx, dy = a["x"] - n["x"], a["y"] - n["y"]
                length = math.hypot(dx, dy) or 1.0
                green = cur is not None and m.id in cur["mov"]
                out.append(SignalHeadView(f"{nid}-{m.id}", n["x"] + dx / length * 10, n["y"] + dy / length * 10,
                                          ("yellow" if left < 2 else "green") if green else "red"))
        return out

"""Tworzy komplet atrap demonstracyjnych połączonych wspólnym stanem."""

def create_demo_backend():
    geometry = DemoGeometry()
    engine = DemoEngine(geometry)
    return Backend(geometry, engine, DemoControl(geometry, engine))
