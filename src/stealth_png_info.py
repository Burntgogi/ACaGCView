# src/stealth_png_info.py
from PIL import Image
from sd_parsers import ParserManager, Eagerness
import json

# Create the parser manager once and reuse it
parser_manager = ParserManager(eagerness=Eagerness.EAGER)

def get_stealth_png_info(image: Image.Image) -> dict | None:
    """
    Extracts metadata from AI-generated PNGs using sd-parsers.
    This handles various formats, including NovelAI's stealth info.
    """
    try:
        prompt_info = parser_manager.parse(image)

        if prompt_info and prompt_info.metadata:
            # The library returns a rich object; we'll convert it to a simple dict
            # for display. We can customize this later if needed.
            return prompt_info.metadata
        
        return None

    except Exception:
        # The library might fail on some images; we'll fail silently.
        return None