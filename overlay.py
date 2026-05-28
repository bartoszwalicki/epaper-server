import os
from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_TEXT_FONT_PATH = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_ICON_FONT_PATH = os.path.join(_FONT_DIR, "weathericons-regular-webfont.ttf")

# Box covers lower-right corner with a 4 px margin from image edges.
_BOX = (265, 235, 395, 295)            # visible border rectangle
_BLEED = (263, 233, 397, 297)          # fat white pre-fill to block dither bleed
_BORDER_W = 2
_ROW1_Y = 238
_ROW2_Y = 266
_ICON_X = 269
_LABEL_X = 297
_TEMP_RIGHT_X = 389                    # right edge for right-aligned temperature


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


TEXT_FONT = _load_font(_TEXT_FONT_PATH, 12)
ICON_FONT = _load_font(_ICON_FONT_PATH, 22)


def draw_weather_overlay(img_L, weather_data):
    """Draw the two-row weather widget in the lower-right corner of img_L.

    Mutates img_L in place. img_L must be a PIL Image in mode 'L' (grayscale).
    weather_data is the list returned by weather.fetch_weather().
    """
    draw = ImageDraw.Draw(img_L)

    # Pre-fill a slightly larger white area so Floyd-Steinberg error diffusion
    # from neighboring photo pixels can't bleed into the visible border.
    draw.rectangle(_BLEED, fill=255)
    draw.rectangle(_BOX, outline=0, width=_BORDER_W, fill=255)

    for row_y, entry in zip((_ROW1_Y, _ROW2_Y), weather_data):
        glyph = entry.get("glyph", "")
        label = f"+{entry['offset_hours']}h"
        temp = f"{round(entry['temp']):d}°"

        draw.text((_ICON_X, row_y - 4), glyph, font=ICON_FONT, fill=0)
        draw.text((_LABEL_X, row_y + 2), label, font=TEXT_FONT, fill=0)

        temp_w = draw.textlength(temp, font=TEXT_FONT)
        draw.text((_TEMP_RIGHT_X - temp_w, row_y + 2), temp, font=TEXT_FONT, fill=0)
