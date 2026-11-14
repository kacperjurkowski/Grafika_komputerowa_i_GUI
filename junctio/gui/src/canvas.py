"""Kanwa: rysuje scenę dostarczoną przez moduł geometrii i przekazuje akcje myszy do modułów.

Tryb "edit"  – edytor skrzyżowania (zaznaczanie, dodawanie, przesuwanie, usuwanie),
tryb "view"  – podgląd symulacji (pojazdy i sygnalizatory, tylko zoom i przesuwanie widoku).
Kanwa nie przechowuje żadnych danych skrzyżowania ani nie wykonuje obliczeń geometrycznych.
"""

# importy bibliotek standardowych

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

# importy modelu danych

from contracts import NODE, ROAD, ElementRef
from assets.theme import colors

# Kolory należą do warstwy GUI; nieznane klucze dostają kolor domyślny.
COLORS = colors.LIGHT
HIT_TOLERANCE_PX = 11

""" Deklaracja obszaru roboczego - widget rysujące scenę i przekazujący zdarzenia do modułów. 
    Udostępnia dwa tryby: edytora oraz podglądu. 
    Przechowuje jedynie stan widoku, a nie dane skrzyżowania. 
"""

class Canvas(QWidget):
    def __init__(self, session, mode="edit"):
        super().__init__()
        self.session, self.mode = session, mode
        self.s, self.o = 6.0, QPointF(0, 0)
        self.tool, self.start, self.cur = "select", None, QPointF()
        self._drag, self._last, self._pan, self._moved, self._fit = None, None, None, False, True
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(400, 300)
        session.scene_changed.connect(self.update)
        session.selection_changed.connect(self.update)
        session.loaded.connect(self.refit)
        if mode == "view":
            session.sim_changed.connect(self.update)

    """ Dopasowuje widok do całej sceny przy najbliższym rysowaniu."""

    def refit(self):
        self.start, self._fit = None, True
        self.update()

    """Ustawia narzędzie w trybie edytora: "wybierz", "węzeł" lub "droga"; anuluje rozpoczętą drogę."""

    def set_tool(self, tool):
        self.tool, self.start = tool, None
        self.setCursor(Qt.ArrowCursor if tool == "select" else Qt.CrossCursor)
        self.update()

    """Zamienia współrzędne świata [m] na punkt ekranu [px] (oś Y jest odwracana)."""

    def pt(self, x, y):
        return QPointF(self.o.x() + x * self.s, self.o.y() - y * self.s)

    """Zamienia punkt ekranu [px] na współrzędne świata [m] (odwrotność pt)."""

    def world(self, p):
        return (p.x() - self.o.x()) / self.s, (self.o.y() - p.y()) / self.s


    """Ustawia skalę i przesunięcie tak, by cała scena mieściła się w widżecie. """

    def fit(self):
        sc = self.session.scene
        b = sc.bounds
        if not b:
            pts = [(n.x, n.y) for n in sc.nodes]
            for r in sc.roads:
                pts.extend(r.center_line)
                pts.extend(r.surface)
            for a in sc.areas:
                pts.extend(a)
            if pts:
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                b = (min(xs), min(ys), max(xs), max(ys))
        if b:
            bw, bh = max(b[2] - b[0], 1), max(b[3] - b[1], 1)
            self.s = max(0.3, min(40.0, (self.width() - 160) / bw, (self.height() - 160) / bh))
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        else:
            self.s, cx, cy = 6.0, 0, 0
        self.o = QPointF(self.width() / 2 - cx * self.s, self.height() / 2 + cy * self.s)
        self._fit = False

    def _path(self, pts, close=False):
        path = QPainterPath(self.pt(*pts[0]))
        for q in pts[1:]:
            path.lineTo(self.pt(*q))
        if close:
            path.closeSubpath()
        return path

    """Rysuje kolejno: tło, siatkę, drogi, powierzchnie skrzyżowań, węzły oraz (tryb view) sygnalizatory i pojazdy."""

    def paintEvent(self, _):
        if self._fit:
            self.fit()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.setClipPath(clip)
        p.fillPath(clip, QColor(COLORS.get("APP_BACKGROUND")))
        self._grid(p)
        sc = self.session.scene
        for r in sc.roads:
            self._road(p, r)
        for a in sc.areas:
            if len(a) > 2:
                p.fillPath(self._path(a, True), QColor(COLORS.get("HELPER_TEXT"))) # potrzeba dodatkowego koloru?
        for n in sc.nodes:
            self._node(p, n)
        if self.mode == "view":
            for h in self.session.heads:
                p.setPen(QPen(QColor(COLORS.get("PANEL")), 1.5))
                p.setBrush(QColor(COLORS.get("car")))          # potrzeba nowego koloru?
                p.drawEllipse(self.pt(h.x, h.y), 5, 5)
            for v in self.session.vehicles:
                self._vehicle(p, v)
        if self.tool == "road" and self.start:
            a = next((n for n in sc.nodes if n.id == self.start), None)
            if a:
                p.setPen(QPen(QColor(COLORS.get("bus")), 2, Qt.DashLine))           # potrzeba nowego koloru?
                p.drawLine(self.pt(a.x, a.y), self.cur)
        p.setBrush(Qt.NoBrush)
        p.setPen(QColor(COLORS.get("HELPER_TEXT")))
        if not self.session.g.available:
            p.drawText(self.rect(), Qt.AlignCenter, "Moduł geometrii nie jest podłączony.")
        hint = ("Kółko myszy: zoom  ·  przeciąganie tła: przesuwanie  ·  Del: usuń zaznaczone" if self.mode == "edit"
                else "Kółko myszy: zoom  ·  przeciąganie: przesuwanie widoku")
        p.drawText(16, self.height() - 14, hint)

    """ Rysowanie siatki w obszarze roboczym (zmniejsza/zwiększa się wraz z powiększeniem) """

    def _grid(self, p):
        step = 10 if self.s * 10 >= 14 else 50
        x0, y1 = self.world(QPointF(0, 0))
        x1, y0 = self.world(QPointF(self.width(), self.height()))
        p.setPen(QPen(QColor(COLORS.get("LINES")), 1))
        for i in range(math.ceil(x0 / step), math.floor(x1 / step) + 1):
            x = self.pt(i * step, 0).x()
            p.drawLine(QPointF(x, 0), QPointF(x, self.height()))
        for j in range(math.ceil(y0 / step), math.floor(y1 / step) + 1):
            y = self.pt(0, j * step).y()
            p.drawLine(QPointF(0, y), QPointF(self.width(), y))

    """ Rysowanie drogi w edycji """

    def _road(self, p, r):
        sel = self.mode == "edit" and self.session.selection == ElementRef(ROAD, r.id)

        # rysowanie pasa drogi
        base = QColor(COLORS.get("HELPER_TEXT")) # nowy kolor do obszaru roboczego?

        if len(r.surface) > 2:
            p.setPen(QPen(QColor(COLORS.get("car")), 3) if sel else QPen(Qt.NoPen))         # nowy kolor na zaznaczenie?
            p.setBrush(base)
            p.drawPath(self._path(r.surface, True))
            p.setBrush(Qt.NoBrush)

            # rysowanie lini na drodze
            p.setPen(QPen(QColor(COLORS.get("ACTIVE_POS")), 1.2, Qt.DashLine))
            for ln in r.lane_lines:
                if len(ln) > 1:
                    p.drawPath(self._path(ln))
        elif len(r.center_line) > 1:  # moduł podał tylko oś drogi – rysujemy ją jako grubą linię
            path = self._path(r.center_line)
            if sel:
                p.setPen(QPen(QColor(COLORS.get("car")), 8, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))        # nowy kolor na zaznaczenie?
                p.drawPath(path)
            p.setPen(QPen(base, 4, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
            p.drawPath(path)

    """ Rysowanie węzła w edycji """

    def _node(self, p, n):        
        c = self.pt(n.x, n.y)        
        edit = self.mode == "edit"        
        active = edit and (self.session.selection == ElementRef(NODE, n.id) or self.start == n.id)        
        p.setPen(QPen(QColor(COLORS.get("car")) if active else QColor(COLORS.get("PANEL")), 2.5))        
        p.setBrush(QColor(COLORS.get(n.kind, "#7A7A7A")))        
        p.drawEllipse(c, 8 if edit else 4, 8 if edit else 4)        
        if edit:            
            p.setBrush(Qt.NoBrush)            
            p.setPen(QColor("#333333"))            
            p.drawText(QPointF(c.x() + 12, c.y() - 10), n.id)

    """ Rysowanie pojazdu podczas symulacji """

    def _vehicle(self, p, v):
        p.save()
        p.translate(self.pt(v.x, v.y))
        p.rotate(-math.degrees(v.heading))  # oś Y ekranu jest odwrócona względem świata
        length, width = max(5.0, v.length * self.s), max(3.0, v.width * self.s)
        p.setPen(QPen(QColor(COLORS.get("PANEL")), 1))
        p.setBrush(QColor(v.color or COLORS.get("car")))                                    # tu wrocic
        p.drawRoundedRect(QRectF(-length / 2, -width / 2, length, width), 2, 2)
        p.restore()

    """ Obsługa myszy -> zaznaczanie, dodawanie, klikanie """

    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position()
        if e.button() in (Qt.MiddleButton, Qt.RightButton):
            self._pan = pos
            return
        if e.button() != Qt.LeftButton:
            return
        if self.mode != "edit" or not self.session.g.available:
            self._pan = pos
            return
        x, y = self.world(pos)
        ref = self.session.hit(x, y, HIT_TOLERANCE_PX / self.s)
        if self.tool == "select":
            self.session.select(ref)
            if ref.kind == NODE:
                self._drag = ref.id
            else:
                self._pan = pos
        elif self.tool == "node":
            self.session.add_node(*self.session.snap(x, y))
        elif self.tool == "road":
            if ref.kind != NODE:
                self.start = None
            elif self.start is None:
                self.start = ref.id
            elif ref.id != self.start:
                self.session.add_road(self.start, ref.id)
                self.start = None
        self.update()

    """ Obsługa ruchu myszy -> przesuwanie, skalowanie """

    def mouseMoveEvent(self, e):
        pos = e.position()
        self.cur = pos
        if self._drag is not None:
            self._last = self.session.snap(*self.world(pos))
            self._moved = True
            self.session.move_node(self._drag, *self._last, False)
        elif self._pan is not None:
            self.o = self.o + (pos - self._pan)
            self._pan = pos
        if self._drag is not None or self._pan is not None or self.start is not None:
            self.update()

    """ Obsługa puszczenia przycisku myszy -> blokowanie elementów w przestrzeni roboczej"""

    def mouseReleaseEvent(self, _):
        if self._drag is not None and self._moved and self._last:
            self.session.move_node(self._drag, *self._last, True)
        self._drag, self._pan, self._moved, self._last = None, None, False, None

    """ Obsługa kółka myszy -> skalowania """

    def wheelEvent(self, e):
        ns = max(0.3, min(80.0, self.s * 1.15 ** (e.angleDelta().y() / 120)))
        f, pos = ns / self.s, e.position()
        self.o, self.s = pos - (pos - self.o) * f, ns
        self.update()

    """ Obsługa klawiatury -> usuwanie przez Del i Backspace; anulowanie przez Esc """

    def keyPressEvent(self, e):
        if self.mode != "edit":
            return
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.session.delete_selected()
        elif e.key() == Qt.Key_Escape:
            self.start = None
            self.update()