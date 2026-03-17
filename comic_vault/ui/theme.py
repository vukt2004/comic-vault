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
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                    stop:0 {t.surface}, 
                                    stop:1 {t.surface_2});
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
    }}

    QFrame#Card {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
    }}

    QLabel#H1 {{
        font-size: 24px;
        font-weight: 800;
        letter-spacing: -0.5px;
    }}

    QLabel#H2 {{
        font-size: 16px;
        font-weight: 700;
        letter-spacing: -0.3px;
    }}

    QLabel#Muted {{
        color: {t.text_muted};
    }}

    /* ===== Inputs ===== */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
        background: {t.surface_2};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        padding: 10px 12px;
        selection-background-color: {t.primary};
        margin: 2px;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 2px solid {t.primary_2};
        margin: 1px;
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
        padding: 9px 15px;
        font-weight: 600;
        transition: all 0.2s ease;
    }}

    QPushButton:hover {{
        background: {t.surface};
        border: 1px solid {t.primary_2};
    }}
    
    QPushButton:pressed {{
        background: rgba(123, 58, 237, 0.1);
    }}

    QPushButton#Primary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {t.primary},
                                    stop:1 {t.primary_2});
        border: none;
        color: white;
        font-weight: 700;
        padding: 10px 18px;
    }}

    QPushButton#Primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {t.primary_2},
                                    stop:1 rgba(167, 139, 250, 0.9));
    }}
    
    QPushButton#Primary:pressed {{
        background: {t.primary};
    }}

    QPushButton#Danger {{
        background: transparent;
        border: 1.5px solid {t.danger};
        color: {t.danger};
        font-weight: 700;
        padding: 9px 14px;
    }}

    QPushButton#Danger:hover {{
        background: rgba(239, 68, 68, 0.15);
        border: 1.5px solid rgba(239, 68, 68, 0.8);
    }}

    QPushButton#Ghost {{
        background: transparent;
        border: 1px solid {t.border};
        color: {t.text};
    }}
    
    QPushButton#Ghost:hover {{
        background: rgba(123, 58, 237, 0.08);
        border: 1px solid {t.primary_2};
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
        background: {t.primary_2};
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
    
    QFrame#ComicCard:hover {{
        border: 1px solid {t.primary};
    }}
    
    QLabel#Cover {{
        background: {t.surface_2};
        border-top-left-radius: {t.radius}px;
        border-top-right-radius: {t.radius}px;
    }}
    
    QPushButton#CornerMenuBtn {{
        background: rgba(15, 26, 43, 0.85);
        border: 1px solid rgba(167, 139, 250, 0.5);
        border-radius: 8px;
        color: {t.text};
        font-size: 14px;
        font-weight: 700;
        padding: 2px;
    }}
    
    QPushButton#CornerMenuBtn:hover {{
        background: rgba(123, 58, 237, 0.2);
        border: 1px solid {t.primary_2};
    }}
    
    QLabel#StatusBadge {{
        background-color: {t.primary};
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    QLabel#Stars {{
        color: {t.warn};
        font-size: 13px;
        font-weight: 600;
    }}

    /* ===== Pages / Header ===== */
    QWidget#Page {{
        background: transparent;
    }}

    QLabel#TopTitle {{
        font-size: 24px;
        font-weight: 900;
        letter-spacing: -0.5px;
    }}

    QLabel#CoverPreview {{
        background: {t.surface_2};
        border: 2px solid rgba(167, 139, 250, 0.4);
        border-radius: {t.radius}px;
    }}

    QLineEdit#CoverPath {{
        background: {t.surface_2};
    }}
    
    /* ===== Form Labels ===== */
    QWidget#FormContainer QLabel {{
        font-weight: 600;
        color: {t.text};
    }}
    """


def apply_theme(app) -> None:
    t = Theme()
    app.setStyleSheet(build_qss(t))
