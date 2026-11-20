"""Panel boczny: nawigacja, ustawienia i karta aktualnego projektu."""

# importy z pakietów standardowych

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout,
                               QWidget)

# importy ikon i etykiet

from assets.theme import icons
from ui_common import label

ICONS = icons.ICONS


"""Pojedyncza pozycja panelu bocznego (ikona + tekst + opcjonalna wartość po prawej)."""

class NavItem(QPushButton):

    def __init__(self, icon_key, text, value=None, checkable=True):
        super().__init__()
        self.setObjectName("nav")
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self._icon_key = icon_key

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)

        # Przywrócenie osobnej etykiety na ikonę, aby nie nachodziła na tekst
        self.ico = QLabel()
        self.ico.setFixedSize(20, 20)
        self.ico.setScaledContents(True)

        if icon_key in ICONS:
            # Sprawdzamy czy w ICONS jest ścieżka (string) czy surowy kod SVG
            val = ICONS[icon_key]
            if val.startswith("<"):
                # Jeśli to SVG w tekście, możemy użyć QIcon / pixmap lub pominąć w tym uproszczeniu,
                # ale standardowo w icons.py masz ścieżki do plików.
                pass
            else:
                self.ico.setPixmap(QPixmap(val))

        self.txt, self.val = QLabel(text), label(value or "", "muted")
        self.txt.setObjectName("navText")
        self.txt.setProperty("active", False)
        for w in (self.ico, self.txt, self.val):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)

        lay.addWidget(self.ico)
        lay.addWidget(self.txt)
        lay.addStretch()
        lay.addWidget(self.val)

        self.toggled.connect(self.set_active)

    def compact(self, on):
        self.txt.setVisible(not on)
        self.val.setVisible(not on and bool(self.val.text()))
        self.ico.setVisible(True) # ikonę można zostawić widoczną w trybie kompaktowym

    def set_active(self, active):
            self.txt.setProperty("active", active)
            self.txt.style().unpolish(self.txt)
            self.txt.style().polish(self.txt)

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
        if "logo" in ICONS:
            self.logo.setPixmap(QPixmap(ICONS["logo"]))

        self.brand = label("Junctio", "brand")
        tb = QToolButton()
        tb.setObjectName("toggle")
        
        if "panel" in ICONS:
            val = ICONS["panel"]
            if not val.startswith("<"):
                tb.setIcon(QIcon(val))
        
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

        self.group.setExclusive(True)

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
        fi.setFixedSize(42, 42)
        if "file" in ICONS and not ICONS["file"].startswith("<"):
            fi.setPixmap(QPixmap(ICONS["file"]))
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