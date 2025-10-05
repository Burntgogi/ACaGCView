# src/exif_info.py
from pathlib import Path
from PIL import Image, ExifTags
from PySide6.QtWidgets import (
    QDialog, QTextEdit, QVBoxLayout, QApplication, QFileDialog, 
    QPushButton, QHBoxLayout, QMessageBox
)

from .stealth_png_info import get_stealth_png_info

def get_metadata_dict(path: Path) -> dict:
    """
    이미지 파일에서 모든 종류의 메타데이터를 추출합니다.
    """
    metadata = {}
    try:
        with Image.open(str(path)) as img:
            # 1. EXIF 정보 추출
            if exif_data := img.getexif():
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        try: value = value.decode('utf-8', errors='ignore')
                        except Exception: pass
                    metadata[str(tag)] = value

            # 2. PNG 텍스트 청크 정보 추출
            if img.format == "PNG" and (info := img.info):
                # DPI 정보는 보통 쓸모 없으므로 제외
                info.pop('dpi', None)
                for k, v in info.items():
                    metadata[k] = v
            
            # 3. AI-generated PNG Info 추출
            if img.format == "PNG":
                if stealth_info := get_stealth_png_info(img):
                    metadata['AI Metadata'] = stealth_info

        return metadata
    except Exception:
        return metadata

class MetadataDialog(QDialog):
    """메타데이터를 표시하고 내용을 업데이트할 수 있는 다이얼로그"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("메타데이터 정보")
        self.resize(500, 600)
        self.current_path: Path | None = None

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        
        # 버튼 추가
        self.copy_button = QPushButton("복사")
        self.save_button = QPushButton("저장")
        self.save_as_button = QPushButton("다른 이름으로 저장")

        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.save_as_button)

        # 메인 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.text_edit)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # 버튼 시그널 연결
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.save_button.clicked.connect(self.save_to_file)
        self.save_as_button.clicked.connect(self.save_as_file)

    def update_content(self, data: dict, current_path: Path):
        self.current_path = current_path
        if data:
            display_data = data.copy()
            text_parts = []
            # AI Metadata가 있으면 상단에 먼저 표시
            ai_info = display_data.pop('AI Metadata', None)

            if ai_info:
                text_parts.append("--- AI Metadata ---")
                for k, v in ai_info.items():
                    # 일부 값은 리스트나 딕셔너리일 수 있으므로 보기 좋게 변환
                    if isinstance(v, list):
                        v_str = ", ".join(map(str, v))
                    elif isinstance(v, dict):
                        v_str = "\n".join([f"  {sub_k}: {sub_v}" for sub_k, sub_v in v.items()])
                    else:
                        v_str = str(v)
                    text_parts.append(f"{k}: {v_str}")
                text_parts.append("\n")

            if text_parts:
                 text_parts.append("--- Other Metadata ---")

            for k, v in sorted(display_data.items()):
                text_parts.append(f"{k}: {v}")
            
            self.text_edit.setText("\n".join(text_parts))
        else:
            self.text_edit.setText("표시할 메타데이터가 없습니다.")

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.text_edit.toPlainText())
        QMessageBox.information(self, "알림", "클립보드에 복사되었습니다.")

    def save_to_file(self):
        if not self.current_path:
            QMessageBox.warning(self, "오류", "이미지 파일 경로를 찾을 수 없습니다.")
            return
        
        if not self.text_edit.toPlainText():
            QMessageBox.warning(self, "오류", "저장할 내용이 없습니다.")
            return

        save_path = self.current_path.with_suffix('.txt')
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            QMessageBox.information(self, "알림", f"{save_path.name} 파일로 저장되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"파일을 저장하는 중 오류가 발생했습니다:\n{e}")

    def save_as_file(self):
        if not self.text_edit.toPlainText():
            QMessageBox.warning(self, "오류", "저장할 내용이 없습니다.")
            return
            
        if not self.current_path:
            start_dir = Path.home()
            default_filename = "metadata.txt"
        else:
            start_dir = self.current_path.parent
            default_filename = self.current_path.with_suffix('.txt').name

        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "다른 이름으로 저장",
            str(start_dir / default_filename),
            "Text Files (*.txt);;All Files (*)"
        )

        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                QMessageBox.information(self, "알림", f"{Path(save_path).name} 파일로 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", f"파일을 저장하는 중 오류가 발생했습니다:\n{e}")
