"""Arkusz stylów aplikacji (wygląd wg makiety, z ręcznymi poprawkami przycisków i paneli)."""

STYLE = """
QMainWindow, QWidget#root { background: #F3F4F6; }
QLabel { color: #1A1A1A; }
QLabel#brand { font-size: 18px; font-weight: 600; }
QLabel#section { color: #7A7A7A; font-size: 12px; padding-left: 12px; }
QLabel#muted { color: #7A7A7A; }
QLabel#small { color: #555555; font-size: 12px; }
QLabel#title { font-size: 22px; font-weight: 600; }
QLabel#h { font-size: 14px; font-weight: 600; }
QFrame#line { background: #D9DADD; }
QFrame#card { background: #E8E8E8; border-radius: 10px; }
QFrame#fileicon { background: white; border-radius: 10px; }
QPushButton#nav { background: transparent; border: none; border-radius: 8px; text-align: left; }
QPushButton#nav:hover { background: #E8E9ED; }
QPushButton#nav:checked { background: white; }
QPushButton#nav QLabel { color: #444444; }
QPushButton#nav:checked QLabel { color: #000000; }
QPushButton#nav QLabel#muted { color: #8A8A8A; font-size: 12px; }
QPushButton#btn:checked, QPushButton#primary { background: #1A1A1A; color: white; }
QToolButton#toggle { border: none; background: transparent; border-radius: 6px; }
QToolButton#toggle:hover { background: #E8E9ED; }
QListWidget::item { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:selected { background: #EDEEF2; color: #000000; }
QSpinBox, QDoubleSpinBox, QComboBox { background: #F4F4F6; border: 1px solid #E0E0E4; border-radius: 6px; padding: 4px 6px; }
QPushButton#tool { background: white; color: #000000; border: 1px solid #D9DADD; border-radius: 8px; padding: 8px 16px; font-family: "Segoe UI"; font-size: 14px; font-weight: 600; }
QPushButton#tool:hover   { background: #E8E9ED; }
QPushButton#tool:checked { background: #E8E9ED; }
QPushButton#tool:pressed { background: #E8E9ED; }
QFrame#panel { background: #F4F4F6; color: #000000; border: 1px solid #E0E0E4; border-radius: 6px; padding: 6px 12px; font-family: "Segoe UI"; font-size: 14px; }
QListWidget { background: #F4F4F6; color: #000000; border: 1px solid #E0E0E4; border-radius: 6px; padding: 6px 12px; font-family: "Segoe UI"; font-size: 14px; }
QDialog, QMessageBox { background: #F3F4F6; }
QMessageBox QLabel { color: #1A1A1A; font-size: 14px; }
QMessageBox QPushButton { background: white; color: #000000; border: 1px solid #D9DADD; border-radius: 8px; padding: 8px 16px; font-family: "Segoe UI"; font-size: 14px; font-weight: 600; }
QMessageBox QPushButton:hover   { background: #E8E9ED; }
QMessageBox QPushButton:pressed { background: #E8E9ED; }

/* --- dodatki do warstwy GUI (informacja o niepodłączonych modułach, tabele, zegar) --- */
QPushButton#tool:disabled { background: #F0F0F2; color: #A0A0A5; }
QLabel#notice { background: #FFF4D6; color: #6B4E00; border-radius: 8px; padding: 8px 12px; }
QLabel#clock { font-size: 18px; font-weight: 600; }
QTableWidget { background: white; color: #000000; border: 1px solid #E0E0E4; border-radius: 6px; gridline-color: #ECECEF; }
QHeaderView::section { background: #F4F4F6; color: #000000; border: none; padding: 6px; font-weight: 600; }
"""
