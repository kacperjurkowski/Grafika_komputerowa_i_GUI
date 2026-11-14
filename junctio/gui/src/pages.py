"""Strony aplikacji: Pliki projektu, Edytor skrzyżowania, Fazy świateł, Symulacja, Statystyki."""

# importy z pakietów standardowych

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox, QFrame, QHBoxLayout, QHeaderView,
                               QLabel, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


# importy modułów GUI, modeli danych, portów modułów backend 

from canvas import Canvas
from contracts import NODE, ROAD, ElementRef
from ui_common import LinePlot, PropertyForm, label, tool_button

"""Wspólny szkielet strony: tytuł i (opcjonalnie) pasek informujący o niepodłączonym module."""

def _page_layout(page, title, notice_text=None, available=True):
    v = QVBoxLayout(page)
    v.setContentsMargins(32, 32, 32, 32)
    v.setSpacing(16)
    v.addWidget(label(title, "title"))
    if notice_text:
        n = label(notice_text, "notice")
        n.setWordWrap(True)
        n.setVisible(not available)
        v.addWidget(n)
    return v

""" Okno startowe - przyciski importu """

class FilesPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        v = _page_layout(self, "Pliki projektu")
        row = QHBoxLayout()
        row.setSpacing(8)
        for text, fn in (("Nowy projekt", win.new_project), ("Otwórz…", win.open_project),
                         ("Zapisz", win.save), ("Zapisz jako…", win.save_as)):
            row.addWidget(tool_button(text, fn, with_shadow=False))
        row.addStretch()
        v.addLayout(row)

        cur = QFrame()
        cur.setObjectName("panel")
        cl = QVBoxLayout(cur)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.addWidget(label("Bieżący projekt", "h"))
        self.info = QLabel()
        cl.addWidget(self.info)
        v.addWidget(cur)

        rec = QFrame()
        rec.setObjectName("panel")
        rl = QVBoxLayout(rec)
        rl.setContentsMargins(20, 16, 20, 16)
        rl.addWidget(label("Ostatnie projekty", "h"))
        self.recent = QListWidget()
        self.recent.itemDoubleClicked.connect(lambda it: win.open_project(it.data(Qt.UserRole)))
        rl.addWidget(self.recent)
        v.addWidget(rec, 1)

    def refresh(self):
        s = self.win.session
        d = s.doc
        self.info.setText(f"<b>{d.name}</b><br><span style='color:#7A7A7A'>"
                          f"{d.path or 'Projekt nie został jeszcze zapisany'}</span><br>"
                          f"Węzły: {len(s.scene.nodes)} · Drogi: {len(s.scene.roads)}")
        self.recent.clear()
        for p in self.win.recent():
            if Path(p).exists():
                it = QListWidgetItem(f"{Path(p).name}      {p}")
                it.setData(Qt.UserRole, p)
                self.recent.addItem(it)

""" Okno edytora - obszar roboczy, narzędzia i panel właściwości. """

class EditorPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session = session
        avail = session.g.available
        self.canvas = Canvas(session, "edit")

        root = _page_layout(self, "Edytor skrzyżowania",
                            "Moduł geometrii nie jest podłączony – edytor czeka na jego implementację.", avail)
        root.setContentsMargins(24, 24, 24, 24)
        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left = QVBoxLayout()
        left.setSpacing(12)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        grp = QButtonGroup(self)
        for key, text in (("select", "Wybierz"), ("node", "Dodaj węzeł"), ("road", "Dodaj drogę")):
            b = tool_button(text, checkable=True)
            b.setChecked(key == "select")
            b.setEnabled(avail)
            b.clicked.connect(lambda _=False, k=key: self.canvas.set_tool(k))
            grp.addButton(b)
            bar.addWidget(b)
        bar.addStretch()
        for text, fn in (("Dopasuj widok", self.canvas.refit), ("Usuń zaznaczone", session.delete_selected)):
            b = tool_button(text, fn)
            b.setEnabled(avail)
            bar.addWidget(b)
        left.addLayout(bar)
        left.addWidget(self.canvas, 1)
        body.addLayout(left, 1)

        side = QFrame()
        side.setObjectName("panel")
        side.setFixedWidth(310)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(16, 16, 16, 16)
        sv.setSpacing(8)
        sv.addWidget(label("Elementy", "h"))
        self.list = QListWidget()
        self.list.itemClicked.connect(lambda it: session.select(ElementRef(*it.data(Qt.UserRole))))
        sv.addWidget(self.list, 1)
        sv.addWidget(label("Właściwości", "h"))
        self.form = PropertyForm()
        self.form.edited.connect(session.set_property)
        sv.addWidget(self.form)
        body.addWidget(side)

        session.scene_changed.connect(self.refresh)
        session.selection_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        s = self.session
        self.list.clear()
        entries = [(f"●  {n.label or f'{n.id}   {n.kind}'}", ElementRef(NODE, n.id)) for n in s.scene.nodes] + \
                  [(f"▬  {r.label or f'{r.id}   {r.from_id} → {r.to_id}'}", ElementRef(ROAD, r.id)) for r in s.scene.roads]
        for text, ref in entries:
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, (ref.kind, ref.id))
            self.list.addItem(it)
            if ref == s.selection:
                self.list.setCurrentItem(it)
        self.form.set_fields((s.selection.kind, s.selection.id), s.properties())

""" Okno modelowania sygnalizacji - fazy świateł, kontrolki sterowania i zegar """

class PhasesPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session, self._busy, self._phases, self._nodes = session, False, [], None
        avail = session.c.available
        v = _page_layout(self, "Fazy świateł",
                         "Moduł sterowania skrzyżowaniem nie jest podłączony – ta strona czeka na jego implementację.",
                         avail)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(label("Skrzyżowanie:", "h"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(200)
        self.combo.currentIndexChanged.connect(lambda _: None if self._busy else self._fill())
        top.addWidget(self.combo)
        top.addStretch()
        self.b_add = tool_button("Dodaj fazę", self._add)
        self.b_del = tool_button("Usuń fazę", self._remove)
        for b in (self.b_add, self.b_del):
            b.setEnabled(avail)
            top.addWidget(b)
        v.addLayout(top)

        self.empty = label("Brak skrzyżowań z sygnalizacją świetlną.", "muted")
        self.empty.setVisible(False)
        v.addWidget(self.empty)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Lp.", "Nazwa fazy", "Czas [s]"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 110)
        self.table.itemChanged.connect(self._cell_edited)
        self.table.currentCellChanged.connect(lambda *_: self._fill_moves())
        body.addWidget(self.table, 3)

        side = QFrame()
        side.setObjectName("panel")
        side.setMinimumWidth(280)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(16, 16, 16, 16)
        sv.addWidget(label("Zielone w wybranej fazie", "h"))
        self.moves = QListWidget()
        self.moves.itemChanged.connect(self._moves_edited)
        sv.addWidget(self.moves)
        body.addWidget(side, 2)
        v.addLayout(body, 1)

        self.cycle = label("", "h")
        v.addWidget(self.cycle)

        session.phases_changed.connect(self._on_change)
        session.scene_changed.connect(self._on_change)
        self.refresh()

    def _on_change(self):
        if self.isVisible():
            self.refresh()

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)

    def refresh(self):
        nodes = self.session.signalized_nodes()
        if nodes != self._nodes:
            self._nodes = nodes
            cur = self.combo.currentData()
            self._busy = True
            self.combo.clear()
            for nid, text in nodes:
                self.combo.addItem(text, nid)
            self.combo.setCurrentIndex(max(self.combo.findData(cur), 0))
            self._busy = False
        self.empty.setVisible(self.session.c.available and not nodes)
        self._fill()

    def _fill(self):
        nid = self.combo.currentData()
        phases = self.session.phases(nid) if nid else []
        row = max(self.table.currentRow(), 0)
        self._busy, self._phases = True, phases
        self.table.setRowCount(len(phases))
        for i, ph in enumerate(phases):
            for col, text in enumerate((str(i + 1), ph.name, f"{ph.duration_s:g}")):
                it = QTableWidgetItem(text)
                if col == 0:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, col, it)
        if phases:
            self.table.setCurrentCell(min(row, len(phases) - 1), 1)
        self.cycle.setText(f"Czas cyklu: {sum(p.duration_s for p in phases):g} s")
        self._busy = False
        self._fill_moves()

    def _fill_moves(self):
        if self._busy:
            return
        self._busy = True
        self.moves.clear()
        nid, row = self.combo.currentData(), self.table.currentRow()
        if nid and 0 <= row < len(self._phases):
            ph = self._phases[row]
            for m in self.session.movements(nid):
                it = QListWidgetItem(m.label)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked if m.id in ph.movements else Qt.Unchecked)
                it.setData(Qt.UserRole, m.id)
                self.moves.addItem(it)
        self._busy = False

    def _current(self):
        nid, row = self.combo.currentData(), self.table.currentRow()
        return (nid, self._phases[row]) if nid and 0 <= row < len(self._phases) else (None, None)

    def _cell_edited(self, item):
        if self._busy or item.column() == 0:
            return
        nid = self.combo.currentData()
        if not nid or not 0 <= item.row() < len(self._phases):
            return
        ph = self._phases[item.row()]
        if item.column() == 1:
            self.session.update_phase(nid, ph.id, name=item.text().strip())
            return
        try:
            value = float(item.text().replace(",", "."))
            if value <= 0:
                raise ValueError
        except ValueError:
            self.session.error.emit("Czas fazy musi być liczbą większą od zera.")
            self._fill()
            return
        self.session.update_phase(nid, ph.id, duration_s=value)

    def _moves_edited(self, _item):
        nid, ph = self._current()
        if self._busy or ph is None:
            return
        ids = [self.moves.item(i).data(Qt.UserRole) for i in range(self.moves.count())
               if self.moves.item(i).checkState() == Qt.Checked]
        self.session.update_phase(nid, ph.id, movements=ids)

    def _add(self):
        nid = self.combo.currentData()
        if nid:
            self.session.add_phase(nid)

    def _remove(self):
        nid, ph = self._current()
        if ph is not None:
            self.session.remove_phase(nid, ph.id)

""" Okno symulacji - start/stop, krokowo, zmiana prędkości i podgląd """

class SimulationPage(QWidget):
    SPEEDS = (0.5, 1.0, 2.0, 5.0, 10.0)

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.avail = session.e.available
        v = _page_layout(self, "Symulacja", "Moduł silnika nie jest podłączony – symulacja czeka na jego implementację.",
                         self.avail)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.b_start = tool_button("▶  Start", session.start)
        self.b_pause = tool_button("⏸  Pauza", session.pause)
        self.b_step = tool_button("⏭  Krok", session.step)
        self.b_reset = tool_button("⟲  Reset", session.reset)
        for b in (self.b_start, self.b_pause, self.b_step, self.b_reset):
            bar.addWidget(b)
        bar.addSpacing(12)
        bar.addWidget(label("Prędkość:", "h"))
        self.speed = QComboBox()
        for sp in self.SPEEDS:
            self.speed.addItem(f"{sp:g}×", sp)
        self.speed.setCurrentIndex(self.SPEEDS.index(1.0))
        self.speed.currentIndexChanged.connect(lambda _: session.set_speed(self.speed.currentData()))
        bar.addWidget(self.speed)
        bar.addStretch()
        self.clock = label("", "clock")
        bar.addWidget(self.clock)
        v.addLayout(bar)
        v.addWidget(Canvas(session, "view"), 1)
        session.sim_changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        st = self.session.status
        self.b_start.setEnabled(self.avail and not st.running)
        self.b_pause.setEnabled(self.avail and st.running)
        self.b_step.setEnabled(self.avail and not st.running)
        self.b_reset.setEnabled(self.avail)
        self.speed.setEnabled(self.avail)
        i = self.speed.findData(st.speed)
        if i >= 0 and i != self.speed.currentIndex():
            self.speed.blockSignals(True)
            self.speed.setCurrentIndex(i)
            self.speed.blockSignals(False)
        self.clock.setText(f"{int(st.time_s // 60):02d}:{st.time_s % 60:04.1f}   ·   pojazdy: {st.vehicles}")

""" Okno statystyk - podsumowanie i wykresy """

class StatsPage(QWidget):
    def __init__(self, session):
        super().__init__()
        self.session, self._snap = session, None
        avail = session.e.available
        v = _page_layout(self, "Statystyki", "Moduł silnika nie jest podłączony – statystyki pojawią się po jego podłączeniu.",
                         avail)
        top = QHBoxLayout()
        top.addWidget(tool_button("Odśwież", self.refresh))
        top.addStretch()
        v.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Wskaźnik", "Wartość"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 200)
        self.table.setFixedWidth(380)
        body.addWidget(self.table)
        right = QVBoxLayout()
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self._show_series)
        right.addWidget(self.combo)
        self.plot = LinePlot()
        right.addWidget(self.plot, 1)
        body.addLayout(right, 1)
        v.addLayout(body, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.refresh() if self.isVisible() else None)
        self._timer.start(1000)
        self.refresh()

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)

    def refresh(self):
        snap = self.session.statistics()
        self._snap = snap
        self.table.setRowCount(len(snap.summary))
        for i, (name, value) in enumerate(snap.summary):
            self.table.setItem(i, 0, QTableWidgetItem(str(name)))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))
        cur = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        for s in snap.series:
            self.combo.addItem(s.name)
        self.combo.setCurrentIndex(max(self.combo.findText(cur), 0))
        self.combo.blockSignals(False)
        self._show_series()

    def _show_series(self, *_):
        i = self.combo.currentIndex()
        self.plot.set_series(self._snap.series[i] if self._snap and 0 <= i < len(self._snap.series) else None)
