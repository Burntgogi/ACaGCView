#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication
from src.viewer import ImageViewer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    start_path = sys.argv[1] if len(sys.argv) > 1 else None
    window = ImageViewer(start_path)
    window.show()
    sys.exit(app.exec())
