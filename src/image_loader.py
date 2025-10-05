# image_loader.py
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import io
from PySide6.QtGui import QPixmap, QImage

def load_image(path: Path) -> QPixmap:
    try:
        img = Image.open(str(path))

        # Convert palette images to RGBA to preserve transparency
        if img.mode == 'P':
            img = img.convert('RGBA')

        # Let Pillow handle AVIF format internally
        if img.format == "AVIF":
            img = img.convert('RGBA')

        data = img.tobytes()
        
        if img.mode == 'RGB':
            # Pillow's byte order is RGB, QImage expects RGB, so it's a direct match.
            qimage = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
        elif img.mode == 'RGBA':
            qimage = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
        elif img.mode == 'L': # Grayscale
            qimage = QImage(data, img.width, img.height, img.width, QImage.Format.Format_Grayscale8)
        else: # Fallback for other modes (like CMYK, etc.)
            # Convert to a supported format before creating the buffer
            if img.mode not in ['RGB', 'RGBA']:
                img = img.convert('RGBA')

            with io.BytesIO() as buf:
                img.save(buf, format='PNG')
                qimage = QImage.fromData(buf.getvalue())

        return QPixmap.fromImage(qimage)

    except UnidentifiedImageError:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {path.suffix}")
    except Exception as e:
        raise RuntimeError(f"이미지 로딩 중 오류 발생: {e}")