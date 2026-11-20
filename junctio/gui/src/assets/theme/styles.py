"""
Arkusz stylów aplikacji. Kolory pochodzą z colors.py, czcionki z fonts.py.

Placeholdery:
    $NAZWA_KOLORU   - klucz ze słownika w colors.py (np. $MAIN_TEXT)
    $FONT_REGULAR / $FONT_MEDIUM / $FONT_SEMIBOLD - nazwy rodzin z fonts.FONTS
Arkusz trzeba budować PO fonts.load_fonts(), ponieważ najpierw należy załadować fonty.
"""

from string import Template
from . import colors, fonts

QSS = Template("""
QWidget                     { font-family: "$FONT_REGULAR"; }
QMainWindow, QWidget#root   { background: $APP_BACKGROUND; }
QLabel                      { color: $MAIN_TEXT; }
QLabel#brand                { font-family: "$FONT_SEMIBOLD"; font-size: 18px; font-weight: 600; }
QLabel#section              { color: $HELPER_TEXT; font-size: 12px; padding-left: 12px; }
QLabel#muted                { color: $HELPER_TEXT; }
QLabel#small                { color: $HELPER_TEXT; font-size: 12px; }
QLabel#title                { font-family: "$FONT_SEMIBOLD"; font-size: 22px; font-weight: 600; }
QLabel#h                    { font-family: "$FONT_SEMIBOLD"; font-size: 14px; font-weight: 600; }
QFrame#line                 { background: $LINES; }
QFrame#card                 { background: $APP_BACKGROUND; border-radius: 10px; }
QFrame#fileicon             { background: $PANEL; border-radius: 10px; }

QPushButton#nav                             { background: transparent; border: none; border-radius: 8px; text-align: left; }
QPushButton#nav:hover                       { background: $APP_BACKGROUND; }
QPushButton#nav:checked                     { color: $MAIN_TEXT; background: $ACTIVE_POS; }
QLabel#navText[active="true"]               { color: $MAIN_TEXT; background: $ACTIVE_POS; font-weight: 500;}
QPushButton#nav QLabel                      { color: $HELPER_TEXT; font-family: "$FONT_REGULAR"; font-weight: 400; }

QPushButton#btn:checked, QPushButton#primary    { background: $MAIN_TEXT; color: $PANEL; }

QToolButton#toggle                              { border: none; background: transparent; border-radius: 6px; }
QToolButton#toggle:hover                        { background: $APP_BACKGROUND; }

QListWidget::item                               { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:selected                      { background: $APP_BACKGROUND; color: $MAIN_TEXT; }
QSpinBox, QDoubleSpinBox, QComboBox             { background: $APP_BACKGROUND; border: 1px solid $FRAMES; border-radius: 6px; padding: 4px 6px; }

QPushButton#tool                { background: $PANEL; color: $MAIN_TEXT; border: 1px solid $FRAMES; border-radius: 8px; padding: 8px 16px; font-family: "$FONT_SEMIBOLD"; font-size: 14px; font-weight: 500; }
QPushButton#tool:hover          { background: $APP_BACKGROUND; }
QPushButton#tool:checked        { background: $APP_BACKGROUND; }
QPushButton#tool:pressed        { background: $APP_BACKGROUND; }

QFrame#panel                    { background: $APP_BACKGROUND; color: $MAIN_TEXT; border: 1px solid $FRAMES; border-radius: 6px; padding: 6px 12px; font-family: "$FONT_REGULAR"; font-size: 14px; }
QListWidget                     { background: $APP_BACKGROUND; color: $MAIN_TEXT; border: 1px solid $FRAMES; border-radius: 6px; padding: 6px 12px; font-family: "$FONT_REGULAR"; font-size: 14px; }
QDialog, QMessageBox            { background: $APP_BACKGROUND; }

QMessageBox QLabel                  { color: $MAIN_TEXT; font-size: 14px; }
QMessageBox QPushButton             { background: $PANEL; color: $MAIN_TEXT; border: 1px solid $FRAMES; border-radius: 8px; padding: 8px 16px; font-family: "$FONT_SEMIBOLD"; font-size: 14px; font-weight: 600; }
QMessageBox QPushButton:hover       { background: $APP_BACKGROUND; }
QMessageBox QPushButton:pressed     { background: $APP_BACKGROUND; }

/* --- dodatki do warstwy GUI (informacja o niepodłączonych modułach, tabele, zegar) --- */
QPushButton#tool:disabled   { background: $APP_BACKGROUND; color: $HELPER_TEXT; }
QLabel#notice               { background: #FFF4D6; color: $MAIN_TEXT; border: 1px solid $FRAMES; border-radius: 8px; padding: 8px 12px; }
QLabel#clock                { font-family: "$FONT_SEMIBOLD"; font-size: 18px; font-weight: 600; }
QTableWidget                { background: $PANEL; color: $MAIN_TEXT; border: 1px solid $FRAMES; border-radius: 6px; gridline-color: $LINES; }
QHeaderView::section        { background: $APP_BACKGROUND; color: $MAIN_TEXT; border: none; padding: 6px; font-family: "$FONT_SEMIBOLD"; font-weight: 600; }
""")


def build(palette=None):
    """Zwraca gotowy QSS. Wywołuj po fonts.load_fonts()."""
    palette = palette or colors.LIGHT
    return QSS.substitute(
        **palette,
        FONT_REGULAR=fonts.FONTS.get("regular", fonts.FALLBACK),
        FONT_MEDIUM=fonts.FONTS.get("medium", fonts.FALLBACK),
        FONT_SEMIBOLD=fonts.FONTS.get("semibold", fonts.FALLBACK),
    )