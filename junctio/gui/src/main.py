"""Junctio – entry-point dla frontendu aplikacji.

Uruchomienie:  python main.py           (uruchomienie z podłączalnymi modułami  - docelowo)
               python main.py --demo    (uruchomienie dema                      - atrapa danych do oglądania GUI)
Podłączanie prawdziwych modułów: wiring.py.
"""

import sys

from PySide6.QtGui     import QFont
from PySide6.QtWidgets import QApplication

from assets.theme import styles, fonts, colors
from window import MainWindow
from wiring import create_backend


def main():
    app = QApplication(sys.argv)

    fonts.load_fonts()                              # po utworzeniu QApplication
    font = QFont(fonts.FONTS["regular"])
    font.setPointSizeF(10.5)
    app.setFont(font)

    app.setStyleSheet(styles.build(colors.LIGHT))   # po load_fonts()

    win = MainWindow(create_backend(demo="--demo" in sys.argv))
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()