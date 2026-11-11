"""Ikony liniowe (SVG renderowane do QPixmap) oraz logo."""

# importy pakietów standardowych
import math

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# importy ikon SVG

ICONS = {
    "logo"      : "./junctio/gui/images/icons/Juntio_Icon.svg",
    "folder"    : "./junctio/gui/images/icons/Pliki_projektu.svg",
    "editor"    : "./junctio/gui/images/icons/Edytor_skrzyzowania.svg",
    "lights"    : "./junctio/gui/images/icons/Fazy_swiatel.svg",
    "play"      : "./junctio/gui/images/icons/Symulacja.svg",
    "stats"     : "./junctio/gui/images/icons/Statystyki.svg",
    "gear"      : "./junctio/gui/images/icons/Ustawienia.svg",
    "palette"   : "./junctio/gui/images/icons/Motyw.svg",
    "lang"      : "./junctio/gui/images/icons/Jezyk.svg",
    "help"      : "./junctio/gui/images/icons/Pomoc.svg",
    "file"      : "./junctio/gui/images/icons/Plik.svg",
    "panel"     : "./junctio/gui/images/icons/Plik.svg",
}