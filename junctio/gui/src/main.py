"""Junctio – entry-point dla frontendu aplikacji.

Uruchomienie:  python main.py           (uruchomienie z podłączalnymi modułami  - docelowo)
               python main.py --demo    (uruchomienie dema                      - atrapa danych do oglądania GUI)
Podłączanie prawdziwych modułów: wiring.py.
"""

# importy z pakietów standardowych
import sys

from PySide6.QtGui          import QFont
from PySide6.QtWidgets      import QApplication

# importy stylów GUI, okna głównego i API do modułów
from styles import STYLE
from window import MainWindow
from wiring import create_backend


# Uruchomienie frontu
def main():
    app = QApplication(sys.argv)
    font = QFont()
    font.setFamilies(["Poppins", "Segoe UI", "Inter", "Arial"])
    font.setPointSizeF(10.5)
    app.setFont(font)
    app.setStyleSheet(STYLE)
    win = MainWindow(create_backend(demo="--demo" in sys.argv))
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
