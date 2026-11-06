"""Panel boczny: nawigacja, ustawienia i karta aktualnego projektu."""

# importy z pakietów standardowych

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout,
                               QWidget)

# importy ikon i etykiet

from icons import logo_pix, pix
from ui_common import label


"""Pojedyncza pozycja panelu bocznego (ikona + tekst + opcjonalna wartość po prawej)."""

class NavItem(QPushButton):

    def __init__(self, icon, text, value=None, checkable=True):
        super().__init__()
        self.setObjectName("nav")
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self._icon = icon
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)
        self.ico, self.txt, self.val = QLabel(), QLabel(text), label(value or "", "muted")
        for w in (self.ico, self.txt, self.val):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.ico)
        lay.addWidget(self.txt)
        lay.addStretch()
        lay.addWidget(self.val)
        self.toggled.connect(self._paint)
        self._paint()

    def _paint(self, *_):
        self.ico.setPixmap(pix(self._icon, "#111111" if self.isChecked() else "#555555"))

    def compact(self, on):
        self.txt.setVisible(not on)
        self.val.setVisible(not on and bool(self.val.text()))

"""Pełny pasek boczny z grupami zakładek """

class Sidebar(QWidget):
    page = Signal(int)   # indeks wybranej strony
    info = Signal(str)   # kliknięto pozycję bez implementacji (np. Ustawienia)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(254)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 12, 0, 25)
        v.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(12)
        self.logo = QLabel()
        self.logo.setPixmap(logo_pix())
        self.brand = label("Junctio", "brand")
        tb = QToolButton()
        tb.setObjectName("toggle")
        tb.setIcon(QIcon(pix("panel", "#555555", 22)))
        tb.setIconSize(QSize(22, 22))
        tb.setFixedSize(34, 34)
        tb.setCursor(Qt.PointingHandCursor)
        tb.clicked.connect(self.toggle)
        for w in (self.logo, self.brand):
            head.addWidget(w)
        head.addStretch()
        head.addWidget(tb)
        v.addLayout(head)
        v.addSpacing(32)
        v.addWidget(self._line())

        self.group, self.items, self.sections = QButtonGroup(self), [], []

        """ Grupy zakładek w pasku bocznym """

        groups = (("Projekt", [("folder", "Pliki projektu")]),
                  ("Tworzenie", [("editor", "Edytor skrzyżowania"), ("lights", "Fazy świateł")]),
                  ("Symulacja", [("play", "Symulacja"), ("stats", "Statystyki")]))
        for title, entries in groups:
            v.addSpacing(24)
            sec = label(title, "section")
            sec.setFixedHeight(16)
            self.sections.append(sec)
            v.addWidget(sec)
            v.addSpacing(8)
            for i, (ic, text) in enumerate(entries):
                if i:
                    v.addSpacing(8)
                it = NavItem(ic, text)
                self.group.addButton(it, len(self.items))
                self.items.append(it)
                v.addWidget(it)
        self.group.idClicked.connect(self.page)

        v.addStretch()
        v.addWidget(self._line())
        v.addSpacing(24)
        self.bottom = []

        """ Zakładki pomocnicze - informacje, ułatwienia dostępu """

        for i, (ic, text, val) in enumerate((("gear", "Ustawienia", None), ("palette", "Motyw", "Jasny"),
                                             ("lang", "Język", "PL"), ("help", "Pomoc", None))):
            if i:
                v.addSpacing(8)
            it = NavItem(ic, text, val, checkable=False)
            it.clicked.connect(lambda _=False, t=text: self.info.emit(t))
            self.bottom.append(it)
            v.addWidget(it)
        v.addSpacing(24)
        v.addWidget(self._line())
        v.addSpacing(24)

        card = QHBoxLayout()
        card.setContentsMargins(6, 0, 0, 0)
        card.setSpacing(12)
        box = QFrame()
        box.setObjectName("fileicon")
        box.setFixedSize(42, 42)
        bl = QHBoxLayout(box)
        bl.setContentsMargins(0, 0, 0, 0)
        fi = QLabel()
        fi.setPixmap(pix("file", "#555555", 20))
        fi.setAlignment(Qt.AlignCenter)
        bl.addWidget(fi)
        self.fname, self.fstat = label("", "small"), label("", "small")
        self.card_txt = QWidget()
        tl = QVBoxLayout(self.card_txt)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)
        tl.addWidget(self.fname)
        tl.addWidget(self.fstat)
        card.addWidget(box)
        card.addWidget(self.card_txt)
        card.addStretch()
        v.addLayout(card)

    @staticmethod
    def _line():
        ln = QFrame()
        ln.setObjectName("line")
        ln.setFixedHeight(1)
        return ln

    def set_current(self, idx):
        self.group.button(idx).setChecked(True)

    def set_file(self, name, status):
        self.fname.setText(name)
        self.fstat.setText(status)

    def toggle(self):
        compact = self.width() > 100
        self.setFixedWidth(52 if compact else 254)
        for w in (self.logo, self.brand, self.card_txt, *self.sections):
            w.setVisible(not compact)
        for it in (*self.items, *self.bottom):
            it.compact(compact)
