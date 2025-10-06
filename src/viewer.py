# src/viewer.py
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QMessageBox, QPushButton, QHBoxLayout
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

        author_label = QLabel("제작자 : AI그림채널 @아주커마니커", alignment=Qt.AlignCenter)

        self.add_context_menu_button = QPushButton("윈도우 우클릭 메뉴에 추가")
        self.add_context_menu_button.clicked.connect(self.setup_context_menu)
        self.remove_context_menu_button = QPushButton("윈도우 우클릭 메뉴에서 제거")
        self.remove_context_menu_button.clicked.connect(self.remove_from_context_menu)

        context_menu_layout = QHBoxLayout()
        context_menu_layout.addWidget(self.add_context_menu_button)
        context_menu_layout.addWidget(self.remove_context_menu_button)

        welcome_layout.addWidget(logo_label)
        welcome_layout.addWidget(author_label)
        welcome_layout.addWidget(help_label)
        welcome_layout.addLayout(context_menu_layout)

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

    def setup_context_menu(self):
        if sys.platform != 'win32':
            QMessageBox.information(self, "알림", "이 기능은 Windows에서만 사용할 수 있습니다.")
            return

        import winreg
        import ctypes

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False

        if not is_admin:
            QMessageBox.warning(self, "권한 필요", "관리자 권한으로 프로그램을 다시 실행한 후 시도해주세요.")
            return

        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 .exe 파일
                exe_path = sys.executable
                command = f'"{exe_path}" "%1"'
            else:
                # Python 스크립트로 직접 실행
                exe_path = sys.executable
                script_path = Path(__file__).resolve().parent.parent / "main.py"
                command = f'"{exe_path}" "{script_path}" "%1"'

            menu_name = "ACaGCView로 열기"
            key_path_template = r"SystemFileAssociations\{ext}\shell\ACaGCView"

            for ext in self.SUPPORTED_EXT:
                # 주 키 생성
                key_path = key_path_template.format(ext=ext)
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
                    winreg.SetValue(key, None, winreg.REG_SZ, menu_name)
                    # 아이콘 경로 추가 (옵션)
                    # winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}"')

                # 커맨드 키 생성
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, fr"{key_path}\command") as key:
                    winreg.SetValue(key, None, winreg.REG_SZ, command)
            
            QMessageBox.information(self, "성공", "우클릭 메뉴에 프로그램이 추가되었습니다.")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"메뉴 추가 중 오류가 발생했습니다:\n{e}")

    def remove_from_context_menu(self):
        if sys.platform != 'win32':
            QMessageBox.information(self, "알림", "이 기능은 Windows에서만 사용할 수 있습니다.")
            return

        import winreg
        import ctypes

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False

        if not is_admin:
            QMessageBox.warning(self, "권한 필요", "관리자 권한으로 프로그램을 다시 실행한 후 시도해주세요.")
            return

        try:
            key_path_template = r"SystemFileAssociations\{ext}\shell\ACaGCView"
            deletions = 0
            for ext in self.SUPPORTED_EXT:
                key_path = key_path_template.format(ext=ext)
                try:
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, fr"{key_path}\command")
                    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
                    deletions += 1
                except FileNotFoundError:
                    continue # 키가 없으면 그냥 지나감
            
            if deletions > 0:
                QMessageBox.information(self, "성공", "우클릭 메뉴에서 프로그램을 제거했습니다.")
            else:
                QMessageBox.information(self, "알림", "제거할 우클릭 메뉴 항목이 없습니다.")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"메뉴 제거 중 오류가 발생했습니다:\n{e}")

    def resizeEvent(self, event):
        if self.file_list and self.idx != -1 and self.image_label.isVisible():
            self.show_image()
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.metadata_dialog: self.metadata_dialog.close()
        super().closeEvent(event)
