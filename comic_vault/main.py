import sys
from PySide6.QtWidgets import QApplication
from comic_vault.ui.main_window import MainWindow
from comic_vault.ui.theme import apply_theme


def main() -> None:
    app = QApplication(sys.argv)
    apply_theme(app)

    win = MainWindow()
    win.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
