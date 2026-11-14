''' Importy fontów do aplikacji '''

import sys
from pathlib import Path
from PySide6.QtGui import QFontDatabase

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

sys.path.append('./assets/fonts')

FONT_FILES = {
    "regular"       : "Poppins-Regular.ttf",
    "medium"        : "Poppins-Medium.ttf",
    "semibold"      : "Poppins-SemiBold.ttf",
}

FONTS       = {}
FALLBACK    = 'Segoe UI'

''' Wczytanie fontów z plików na podstawie wpisów w słowniku FONT_FILES. Dodanie nowych fontów przez dodanie par w słowniku.'''
def load_fonts():
    for key, filename in FONT_FILES.items():
        font_id     = QFontDatabase.addApplicationFont(str(FONTS_DIR / filename))
        families    = QFontDatabase.applicationFontFamilies(font_id) if font_id != -1 else []
        if families:
            FONTS[key] = families[0]
        else:
            print(f"Nie udało się wczytać fontu: {filename}")
            FONTS[key] = FALLBACK

