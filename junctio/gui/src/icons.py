"""Ikony liniowe (SVG renderowane do QPixmap) oraz logo."""

# importy pakietów standardowych
import math

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# importy ikon SVG

_teeth = "".join(
    f'<line x1="{12 + 7 * math.cos(a):.2f}" y1="{12 + 7 * math.sin(a):.2f}" '
    f'x2="{12 + 9.5 * math.cos(a):.2f}" y2="{12 + 9.5 * math.sin(a):.2f}"/>'
    for a in (i * math.pi / 4 for i in range(8)))
ICONS = {
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "editor": '<circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 5h4a2 2 0 0 1 2 2v10a2 2 0 0 0 2 2h2"/>',
    "lights": '<rect x="8" y="2.5" width="8" height="19" rx="4"/><circle cx="12" cy="7.5" r=".6"/><circle cx="12" cy="12" r=".6"/><circle cx="12" cy="16.5" r=".6"/>',
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "stats": '<path d="M3 20h18M4 16l5-5 4 3 7-8"/>',
    "gear": f'<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/>{_teeth}',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.8-1 1.4-2-.4-1 .3-2.2 1.4-2.2H17a4 4 0 0 0 4-4c0-5-4-9.8-9-9.8z"/><circle cx="7.5" cy="11" r=".7"/><circle cx="10" cy="7" r=".7"/><circle cx="15" cy="7.5" r=".7"/>',
    "lang": '<path d="M4 6h9M8.5 4v2M6 6c.5 3 3 6 6 7.5M11 6c-.5 3-3 6-6.5 8M13 20l4-9 4 9M14.6 17h4.8"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7"/><circle cx="12" cy="17" r=".6"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "panel": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
}

""" Funkcje generujące ikony SVG """

def pix(name, color="#555555", size=20):
    """Ikona SVG jako QPixmap o zadanym kolorze i rozmiarze (podwójna rozdzielczość)."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    QSvgRenderer(QByteArray(svg.encode())).render(p)
    p.end()
    pm.setDevicePixelRatio(2)
    return pm

""" Funkcja generująca logo aplikacji """

def logo_pix(size=32):
    """Logo aplikacji jako QPixmap."""
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(2, 2)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#111111"))
    p.drawRoundedRect(QRectF(0, 0, size, size), 8, 8)
    p.setBrush(Qt.white)
    p.drawEllipse(QPointF(16, 9.5), 2.6, 2.6)
    p.drawRoundedRect(QRectF(12.5, 14, 7, 11), 2, 2)
    p.end()
    pm.setDevicePixelRatio(2)
    return pm
