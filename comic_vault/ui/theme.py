from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    # Base
    bg: str = "#0B1220"
    surface: str = "#0F1A2B"
    surface_2: str = "#101F36"
    border: str = "#20324C"
    text: str = "#E6EDF7"
    text_muted: str = "#A6B3C7"

    # Accents
    primary: str = "#7C3AED"
    primary_2: str = "#A78BFA"
    danger: str = "#EF4444"
    warn: str = "#F59E0B"
    success: str = "#22C55E"

    # Sizes
    radius: int = 14
    radius_sm: int = 10


def build_qss(t: Theme) -> str:
    return f"""
    /* ===== Global ===== */
    QWidget {{
        background: {t.bg};
        color: {t.text};
        font-family: "Segoe UI", "Inter", "Arial";
        font-size: 13px;
    }}

    QMainWindow::separator {{
        background: {t.border};
        width: 1px;
        height: 1px;
    }}

    /* ===== Common containers ===== */
    QWidget#TopBar {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
    }}

    QFrame#Card {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
    }}

    QLabel#H1 {{
        font-size: 22px;
        font-weight: 800;
    }}

    QLabel#H2 {{
        font-size: 16px;
        font-weight: 700;
    }}

    QLabel#Muted {{
        color: {t.text_muted};
    }}

    /* ===== Inputs ===== */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
        background: {t.surface_2};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        padding: 8px 10px;
        selection-background-color: {t.primary};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {t.primary_2};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}

    /* ===== Buttons ===== */
    QPushButton {{
        background: {t.surface_2};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        padding: 8px 14px;
    }}

    QPushButton:hover {{
        border: 1px solid {t.primary_2};
    }}

    QPushButton:pressed {{
        background: {t.surface};
    }}

    QPushButton#Primary {{
        background: {t.primary};
        border: 1px solid {t.primary};
        color: white;
        font-weight: 700;
    }}

    QPushButton#Primary:hover {{
        background: {t.primary_2};
        border: 1px solid {t.primary_2};
    }}

    QPushButton#Danger {{
        background: transparent;
        border: 1px solid {t.danger};
        color: {t.danger};
        font-weight: 700;
    }}

    QPushButton#Danger:hover {{
        background: rgba(239, 68, 68, 0.12);
    }}

    QPushButton#Ghost {{
        background: transparent;
        border: 1px solid {t.border};
    }}

    /* ===== Scroll ===== */
    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 6px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.border};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t.primary};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* ===== Custom: ComicCard ===== */
    QFrame#ComicCard {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
    }}
    QLabel#Cover {{
        background: {t.surface_2};
        border-top-left-radius: {t.radius}px;
        border-top-right-radius: {t.radius}px;
    }}
    QWidget#Overlay {{
        background: rgba(0, 0, 0, 0.35);
        border-top-left-radius: {t.radius}px;
        border-top-right-radius: {t.radius}px;
    }}
    QPushButton#OverlayBtn {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: 14px;
        min-width: 54px;
        min-height: 40px;
        font-size: 12px;
        font-weight: 700;
    }}
    QPushButton#OverlayBtn:hover {{
        border: 1px solid {t.primary_2};
    }}
    QPushButton#OverlayBtnDanger {{
        background: {t.surface};
        border: 1px solid {t.danger};
        color: {t.danger};
        border-radius: 14px;
        min-width: 54px;
        min-height: 40px;
        font-size: 12px;
        font-weight: 700;
    }}
    QLabel#Stars {{
        color: {t.warn};
        font-size: 16px;
    }}

    /* ===== Pages / Header ===== */
    QWidget#Page {{
        background: transparent;
    }}

    QLabel#TopTitle {{
        font-size: 22px;
        font-weight: 900;
    }}

    QLabel#CoverPreview {{
        background: {t.surface_2};
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
    }}

    QLineEdit#CoverPath {{
        background: {t.surface_2};
    }}
    """


def apply_theme(app) -> None:
    t = Theme()
    app.setStyleSheet(build_qss(t))
