# src/viewer.py
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QMessageBox
)

from .image_loader import load_image
from .exif_info import get_metadata_dict, MetadataDialog

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(".").resolve()
    return base_path / relative_path


class ImageViewer(QMainWindow):
    SUPPORTED_EXT = {'.png', '.jpg', '.jpeg', '.jfif', '.bmp', '.webp', '.avif'}
    HELP_TEXT = """
    <h3 style='text-align: center;'>키보드 단축키:</h3>
    <ul>
        <li><b>&larr; / &rarr;</b> : 이전 / 다음 이미지 보기</li>
        <li><b>Home / End</b> : 폴더의 첫 / 마지막 이미지로 이동</li>
        <li><b>Tab</b> : 사진의 모든 메타데이터 정보 보기 (토글)</li>
    </ul>
"""

    def __init__(self, start_path=None):
        super().__init__()
        self.setWindowTitle("ACaGCView")
        self.resize(1024, 768)

        # --- Welcome Screen Setup ---
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel(alignment=Qt.AlignCenter)
        logo_pixmap = QPixmap(str(resource_path('2.webp')))
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaledToWidth(256, Qt.SmoothTransformation))
        
        help_label = QLabel(self.HELP_TEXT, alignment=Qt.AlignCenter)
        help_label.setWordWrap(True)

        welcome_layout.addWidget(logo_label)
        welcome_layout.addWidget(help_label)
        
        # --- Image Label Setup ---
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setWordWrap(True)

        # --- Central Widget Setup ---
        self.central_widget = QWidget()
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.addWidget(self.welcome_widget)
        self.central_layout.addWidget(self.image_label)
        self.setCentralWidget(self.central_widget)

        self.setAcceptDrops(True)

        self.current_dir: Path | None = None
        self.file_list: list[Path] = []
        self.idx: int = -1
        self.metadata_dialog: MetadataDialog | None = None
        self.metadata_cache: dict[Path, dict] = {}

        if start_path:
            self.load_path(Path(start_path))
        else:
            self.show_welcome_screen()

    def show_welcome_screen(self):
        self.welcome_widget.show()
        self.image_label.hide()
        self.setWindowTitle("ACaGCView")

    def load_path(self, path: Path):
        if not path.exists(): return

        if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXT:
            self.current_dir = path.parent
        elif path.is_dir():
            self.current_dir = path
        else:
            return

        self.metadata_cache.clear() # 새 폴더를 로드하면 캐시 초기화
        self.file_list = sorted([p for p in self.current_dir.iterdir() if p.suffix.lower() in self.SUPPORTED_EXT])
        
        if path.is_file():
            self.idx = self.file_list.index(path) if path in self.file_list else 0
        else:
            self.idx = 0 if self.file_list else -1
        
        self.show_image()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            path = Path(event.mimeData().urls()[0].toLocalFile())
            if path.suffix.lower() in self.SUPPORTED_EXT or path.is_dir():
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        self.load_path(Path(event.mimeData().urls()[0].toLocalFile()))

    def show_image(self):
        if not self.file_list or self.idx == -1:
            self.show_welcome_screen()
            return

        self.welcome_widget.hide()
        self.image_label.show()

        path = self.file_list[self.idx]
        try:
            pixmap = load_image(path)
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setWindowTitle(f"{path.name} ({self.idx + 1}/{len(self.file_list)}) - ACaGCView")
            self.update_info_windows()
        except Exception as e:
            QMessageBox.warning(self, "오류", f"이미지 로딩 실패:\n{e}")
            self.file_list.pop(self.idx)
            if self.idx >= len(self.file_list): self.idx = len(self.file_list) - 1
            self.show_image()

    def get_cached_metadata(self, path: Path) -> dict:
        """캐시에서 메타데이터를 가져오거나, 없으면 새로 추출하여 캐시에 저장합니다."""
        if path in self.metadata_cache:
            return self.metadata_cache[path]
        else:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            data = get_metadata_dict(path)
            QApplication.restoreOverrideCursor()
            self.metadata_cache[path] = data
            return data

    def update_info_windows(self):
        if self.metadata_dialog and self.metadata_dialog.isVisible():
            data = self.get_cached_metadata(self.file_list[self.idx])
            self.metadata_dialog.update_content(data, self.file_list[self.idx])

    def keyPressEvent(self, e):
        if not self.file_list and e.key() != Qt.Key_Tab:
            super().keyPressEvent(e)
            return

        key = e.key()
        
        if key == Qt.Key_Right: self.navigate_image(1)
        elif key == Qt.Key_Left: self.navigate_image(-1)
        elif key == Qt.Key_Home: self.navigate_image(-self.idx)
        elif key == Qt.Key_End: self.navigate_image(len(self.file_list) - 1 - self.idx)
        elif key == Qt.Key_Tab: self.toggle_metadata_dialog()
        else: super().keyPressEvent(e)

    def navigate_image(self, step: int):
        if not self.file_list: return
        new_idx = (self.idx + step) % len(self.file_list)
        self.idx = new_idx
        self.show_image()

    def toggle_metadata_dialog(self):
        if not self.metadata_dialog:
            self.metadata_dialog = MetadataDialog(self)
        
        if self.metadata_dialog.isVisible():
            self.metadata_dialog.hide()
        else:
            if self.file_list:
                data = self.get_cached_metadata(self.file_list[self.idx])
                self.metadata_dialog.update_content(data, self.file_list[self.idx])
                self.metadata_dialog.show()

    def resizeEvent(self, event):
        if self.file_list and self.idx != -1 and self.image_label.isVisible():
            self.show_image()
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.metadata_dialog: self.metadata_dialog.close()
        super().closeEvent(event)
