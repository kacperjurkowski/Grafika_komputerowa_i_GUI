"""Okno główne: układ, nawigacja między stronami i obsługa plików projektu."""

# importy z pakietów standardowych

from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget,
                               QVBoxLayout, QWidget, QApplication)

# importy okien aplikacji, paska bocznego i łącznika Session
from pages import EditorPage, FilesPage, PhasesPage, SimulationPage, StatsPage
from session import Session
from sidebar import Sidebar

""" Okno główne: panel boczny, strony aplikacji i operacje na plikach projektu. 
    Sama praca na plikach należy do modułu geometrii; 
    okno zajmuje się oknami dialogowymi, pytaniem o niezapisane zmiany i listą ostatnich projektów (QSettings). 
"""

class MainWindow(QMainWindow):
    def __init__(self, backend):
        super().__init__()
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width()* 0.85), int(screen.height() * 0.85))
        self.setWindowIcon(QIcon("./junctio/gui/images/icons/Juntio_Icon.svg"))
        self.setMinimumSize(1000, 640)
        self.move(screen.center() - self.rect().center())
        self.session = Session(backend)
        self.settings = QSettings("Junctio", "Junctio")

        root = QWidget()
        root.setObjectName("root")
        lay = QHBoxLayout(root)
        lay.setContentsMargins(30, 20, 20, 20)
        lay.setSpacing(29)
        self.sidebar = Sidebar()
        lay.addWidget(self.sidebar)
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        cl.addWidget(self.stack)
        lay.addWidget(card, 1)
        self.setCentralWidget(root)

        # Kolejność stron musi odpowiadać kolejności pozycji w Sidebar.
        self.files = FilesPage(self)
        for pg in (self.files, EditorPage(self.session), PhasesPage(self.session),
                   SimulationPage(self.session), StatsPage(self.session)):
            self.stack.addWidget(pg)

        self.sidebar.page.connect(self.stack.setCurrentIndex)
        self.sidebar.info.connect(lambda t: QMessageBox.information(self, "Junctio", f"„{t}” – funkcja w przygotowaniu."))
        self.session.error.connect(lambda m: QMessageBox.warning(self, "Junctio", m))
        self.session.document_changed.connect(self._sync)
        timer = QTimer(self)
        timer.timeout.connect(self._sync)
        timer.start(30_000)

        for seq, fn in ((QKeySequence.New, self.new_project), (QKeySequence.Open, self.open_project),
                        (QKeySequence.Save, self.save), (QKeySequence("Ctrl+Shift+S"), self.save_as)):
            QShortcut(QKeySequence(seq), self, activated=lambda f=fn: f())

        self.sidebar.set_current(0)
        self._sync()

    def _sync(self):
        d = self.session.doc
        self.sidebar.set_file(d.name, self.session.doc_status())
        self.setWindowTitle(f"Junctio - symulator skrzyżowań – {d.name}{' *' if d.dirty else ''}")
        self.files.refresh()

    # --- ostatnie pliki ---

    """Lista ostatnio używanych plików (z QSettings)."""

    def recent(self):
        r = self.settings.value("recent") or []
        return [r] if isinstance(r, str) else list(r)

    """Dodaje plik na początek listy ostatnich (maksymalnie 8 wpisów)."""

    def _remember(self, path):
        self.settings.setValue("recent", [str(path)] + [p for p in self.recent() if p != str(path)][:7])
        self.files.refresh()

    # --- operacje na plikach (sama praca na plikach należy do modułu geometrii) ---

    """Pyta o zapis niezapisanych zmian; zwraca False, gdy użytkownik anuluje."""

    def _confirm(self):
        if not self.session.doc.dirty:
            return True
        r = QMessageBox.question(self, "Niezapisane zmiany", "Zapisać zmiany w projekcie?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    """Tworzy nowy projekt (po potwierdzeniu ewentualnych niezapisanych zmian)."""

    def new_project(self):
        if self._confirm():
            self.session.new_project()

    """Otwiera projekt ze wskazanej ścieżki albo z okna wyboru pliku."""

    def open_project(self, path=None):
        if not self._confirm():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Otwórz projekt", "",
                                                  f"{self.session.g.file_filter};;Wszystkie pliki (*)")
        if path and self.session.open_project(path):
            self._remember(path)

    """Zapisuje projekt pod bieżącą ścieżką; bez ścieżki otwiera „Zapisz jako…”."""

    def save(self):
        path = self.session.doc.path
        return self._write(path) if path else self.save_as()

    """Pyta o ścieżkę i zapisuje projekt; zwraca True, gdy się powiodło."""

    def save_as(self):
        g = self.session.g
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz projekt jako",
                                              f"{self.session.doc.name}{g.default_suffix}", g.file_filter)
        if not path:
            return False
        return self._write(path if Path(path).suffix else path + g.default_suffix)

    """Zapisuje projekt przez moduł geometrii i dodaje plik do ostatnich."""

    def _write(self, path):
        if not self.session.save_project(path):
            return False
        self._remember(path)
        return True

    """Przy zamykaniu pyta o niezapisane zmiany."""

    def closeEvent(self, e):
        e.accept() if self._confirm() else e.ignore()
