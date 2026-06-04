import os
from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_TEXT_FONT_PATH = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_ICON_FONT_PATH = os.path.join(_FONT_DIR, "weathericons-regular-webfont.ttf")

# Vertical box anchored to the lower-right corner with a 4 px margin
# from the image edges. Two forecast blocks stacked vertically.
_BOX_W = 60
_BOX_H = 130
_BOX_LEFT = 400 - 4 - _BOX_W       # 336
_BOX_TOP = 300 - 4 - _BOX_H        # 166
_BOX_RIGHT = _BOX_LEFT + _BOX_W    # 396
_BOX_BOTTOM = _BOX_TOP + _BOX_H    # 296

_BORDER_W = 2
_BLOCK_H = (_BOX_H - _BORDER_W) // 2     # 64
_SEPARATOR_Y = _BOX_TOP + _BLOCK_H        # 230

# Within each block: the icon is vertically centred in the box between the
# upper line (the top border for the first block, the separator for the rest)
# and the label, then the label and temperature sit at fixed offsets below.
_LABEL_Y_OFFSET = 31
_TEMP_Y_OFFSET = 45


def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


TEXT_FONT = _load_font(_TEXT_FONT_PATH, 12)
ICON_FONT = _load_font(_ICON_FONT_PATH, 26)


def _draw_centered(draw, text, font, cx, y):
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=0)


def _draw_icon(draw, glyph, font, cx, box_top, box_bottom):
    """Draw an icon glyph centred horizontally on ``cx`` and vertically within
    the box ``[box_top, box_bottom]``.

    Glyphs in the Weather Icons font have varying internal bearings and
    heights, so we measure the glyph's visible bbox and centre that visible
    extent in the box (rather than the font's nominal line box).
    """
    if not glyph:
        return
    w = draw.textlength(glyph, font=font)
    left, top, right, bottom = font.getbbox(glyph)
    glyph_h = bottom - top
    visible_top = box_top + (box_bottom - box_top - glyph_h) / 2
    draw.text((cx - w / 2, round(visible_top - top)), glyph, font=font, fill=0)


def draw_weather_overlay(img_1bit, weather_data):
    """Paste the vertical weather widget onto the lower-right of a 1-bit image.

    The widget is composed on a grayscale canvas and converted to 1-bit
    with threshold (no Floyd-Steinberg), so the photo's dithering does
    not bleed into the widget and the glyphs/text stay crisp.

    img_1bit: PIL.Image in mode '1' (the dithered final frame).
    weather_data: list of two dicts returned by weather.fetch_weather().
    """
    widget = Image.new("L", (_BOX_W, _BOX_H), 255)
    draw = ImageDraw.Draw(widget)

    draw.rectangle((0, 0, _BOX_W - 1, _BOX_H - 1), outline=0, width=_BORDER_W)
    sep_y_local = _BLOCK_H
    draw.line((_BORDER_W, sep_y_local, _BOX_W - 1 - _BORDER_W, sep_y_local),
              fill=0, width=1)

    cx = _BOX_W // 2
    for i, entry in enumerate(weather_data):
        block_top = i * _BLOCK_H
        # The icon box spans from the upper line (2 px top border for the
        # first block, 1 px separator for the rest) down to the label.
        box_top = _BORDER_W if i == 0 else block_top + 1
        box_bottom = block_top + _LABEL_Y_OFFSET
        glyph = entry.get("glyph", "")
        label = f"{entry['hour']:02d}h"
        temp = f"{round(entry['temp']):d}°"
        _draw_icon(draw, glyph, ICON_FONT, cx, box_top, box_bottom)
        _draw_centered(draw, label, TEXT_FONT, cx, block_top + _LABEL_Y_OFFSET)
        _draw_centered(draw, temp, TEXT_FONT, cx, block_top + _TEMP_Y_OFFSET)

    widget_1 = widget.convert("1", dither=Image.Dither.NONE)
    img_1bit.paste(widget_1, (_BOX_LEFT, _BOX_TOP))
