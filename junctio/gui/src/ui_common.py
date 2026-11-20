"""Wspólne, drobne widgety i funkcje pomocnicze GUI."""

# importy z pakietów standardowych

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGraphicsDropShadowEffect,
                               QLabel, QPushButton, QSpinBox, QWidget)


""" Etykieta z tekstem"""

def label(text, name=""):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    return lb

""" Efekt cienia """

def shadow():
    return QGraphicsDropShadowEffect(blurRadius=12, xOffset=0, yOffset=3, color=QColor(0, 0, 0, 70))

""" Przycisk w stylu 'tool' (z zestawu STYLE) (biały, z obrysem), opcjonalnie z cieniem. """

def tool_button(text, handler=None, checkable=False, with_shadow=True):
    b = QPushButton(text)
    b.setObjectName("tool")
    b.setCursor(Qt.PointingHandCursor)
    b.setCheckable(checkable)
    if with_shadow:
        b.setGraphicsEffect(shadow())
    if handler:
        b.clicked.connect(lambda _=False, f=handler: f())
    return b

""" Lista właściwości elementów obecnych na obszarze roboczym """

class PropertyForm(QWidget):
    edited = Signal(str, object)  # klucz pola, nowa wartość

    def __init__(self):
        super().__init__()
        self.setStyleSheet("color: #000000;")
        self._form = QFormLayout(self)
        self._form.setContentsMargins(0, 0, 0, 0)
        self._widgets, self._sig, self._busy = {}, None, False

    """token identyfikuje zaznaczony element; formularz jest budowany od nowa tylko, gdy zmieni się układ pól."""

    def set_fields(self, token, fields):
        sig = (token, tuple((f.key, f.kind, f.readonly) for f in fields))
        self._busy = True
        if sig != self._sig:
            self._rebuild(fields)
            self._sig = sig
        for f in fields:
            self._load(self._widgets[f.key], f)
        self._busy = False

    def _rebuild(self, fields):
        while self._form.rowCount():
            self._form.removeRow(0)
        self._widgets = {}
        if not fields:
            self._form.addRow(label("Zaznacz węzeł lub drogę.", "muted"))
            return
        for f in fields:
            w = self._make(f)
            self._widgets[f.key] = w
            self._form.addRow("" if f.kind == "bool" else f.label, w)

    def _make(self, f):
        if f.kind in ("int", "float"):
            is_int = f.kind == "int"
            w = QSpinBox() if is_int else QDoubleSpinBox()
            lo = f.minimum if f.minimum is not None else -1_000_000
            hi = f.maximum if f.maximum is not None else 1_000_000
            w.setRange(int(lo), int(hi)) if is_int else w.setRange(float(lo), float(hi))
            if not is_int:
                w.setDecimals(f.decimals)
            w.setSingleStep(int(f.step or 1) if is_int else float(f.step or 1.0))
            w.setSuffix(f.suffix)
            w.setKeyboardTracking(False)
            w.valueChanged.connect(lambda v, k=f.key: self._emit(k, v))
        elif f.kind == "bool":
            w = QCheckBox(f.label)
            w.toggled.connect(lambda v, k=f.key: self._emit(k, v))
        elif f.kind == "choice":
            w = QComboBox()
            for value, text in f.choices:
                w.addItem(text, value)
            w.currentIndexChanged.connect(lambda _, k=f.key, c=w: self._emit(k, c.currentData()))
        else:
            w = QLabel()
        if f.readonly and f.kind != "text":
            w.setEnabled(False)
        return w

    """Wpisuje wartość pola do listy właściwości."""

    @staticmethod
    def _load(w, f):
        if isinstance(w, QDoubleSpinBox):
            w.setValue(float(f.value))
        elif isinstance(w, QSpinBox):
            w.setValue(int(f.value))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(f.value))
        elif isinstance(w, QComboBox):
            w.setCurrentIndex(max(w.findData(f.value), 0))
        else:
            w.setText(str(f.value))

    def _emit(self, key, value):
        if not self._busy:
            self.edited.emit(key, value)


"""Prosty wykres liniowy jednej serii (contracts.Series)."""

class LinePlot(QWidget):

    def __init__(self):
        super().__init__()
        self._series = None
        self.setMinimumHeight(220)

    def set_series(self, series):
        self._series = series
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QPainterPath()
        bg.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.fillPath(bg, QColor("#FFFFFF"))
        s = self._series
        if not s or len(s.points) < 2:
            p.setPen(QColor("#8A8A8A"))
            p.drawText(self.rect(), Qt.AlignCenter, "Brak danych do wyświetlenia")
            return
        r = QRectF(48, 28, self.width() - 48 - 16, self.height() - 28 - 30)
        xs, ys = [q[0] for q in s.points], [q[1] for q in s.points]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if x1 == x0:
            x1 = x0 + 1
        if y1 == y0:
            y1 = y0 + 1

        def pt(q):
            return QPointF(r.left() + (q[0] - x0) / (x1 - x0) * r.width(),
                           r.bottom() - (q[1] - y0) / (y1 - y0) * r.height())

        p.setPen(QPen(QColor("#E2E2E6"), 1))
        for k in range(5):
            y = r.top() + k * r.height() / 4
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        p.setPen(QColor("#555555"))
        p.drawText(4, int(r.top()) + 4, f"{y1:.1f}")
        p.drawText(4, int(r.bottom()), f"{y0:.1f}")
        p.drawText(int(r.left()), self.height() - 8, f"{x0:.0f} s")
        p.drawText(int(r.right()) - 40, self.height() - 8, f"{x1:.0f} s")
        path = QPainterPath(pt(s.points[0]))
        for q in s.points[1:]:
            path.lineTo(pt(q))
        p.setPen(QPen(QColor("#2F6FED"), 2))
        p.drawPath(path)
        p.setPen(QColor("#1A1A1A"))
        p.drawText(int(r.left()), 16, f"{s.name} [{s.unit}]" if s.unit else s.name)
