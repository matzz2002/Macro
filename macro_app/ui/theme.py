from __future__ import annotations


DARK_QSS = """
QWidget {
    background: #0f1117;
    color: #e5e7eb;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}
QFrame#Panel {
    background: #151924;
    border: 1px solid #242b3a;
    border-radius: 14px;
}
QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget, QTableWidget {
    background: #0b0f17;
    border: 1px solid #2a3345;
    border-radius: 8px;
    padding: 6px;
    selection-background-color: #7c3aed;
}
QPushButton {
    background: #232a3b;
    border: 1px solid #343d52;
    border-radius: 9px;
    padding: 8px 10px;
}
QPushButton:hover {
    background: #2d3650;
}
QPushButton#PrimaryButton {
    background: #7c3aed;
    border-color: #8b5cf6;
    color: white;
    font-weight: 600;
}
QPushButton#DangerButton {
    background: #991b1b;
    border-color: #dc2626;
    color: white;
}
QHeaderView::section {
    background: #151924;
    color: #cbd5e1;
    border: 0;
    padding: 6px;
}
QStatusBar {
    background: #0b0f17;
    color: #cbd5e1;
}
"""


LIGHT_QSS = """
QWidget {
    background: #f4f6fb;
    color: #111827;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}
QFrame#Panel {
    background: #ffffff;
    border: 1px solid #d7dce8;
    border-radius: 14px;
}
QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px;
    selection-background-color: #8b5cf6;
}
QPushButton {
    background: #e8edf7;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    padding: 8px 10px;
}
QPushButton:hover {
    background: #dce4f2;
}
QPushButton#PrimaryButton {
    background: #7c3aed;
    border-color: #7c3aed;
    color: white;
    font-weight: 600;
}
QPushButton#DangerButton {
    background: #dc2626;
    border-color: #b91c1c;
    color: white;
}
QHeaderView::section {
    background: #eef2ff;
    color: #111827;
    border: 0;
    padding: 6px;
}
QStatusBar {
    background: #ffffff;
    color: #111827;
}
"""


def stylesheet(theme: str) -> str:
    return LIGHT_QSS if theme == "light" else DARK_QSS
