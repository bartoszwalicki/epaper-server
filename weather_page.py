"""Full-page (400x300) 2-day weather forecast layout for the e-paper panel.

Rendered server-side and packed exactly like a photo so the device just blits
the resulting 1-bit bitmap. Composed on a grayscale ("L") canvas and converted
to mode "1" with dither=NONE so text and icons stay crisp.
"""
from PIL import Image, ImageDraw

from overlay import (
    _ICON_FONT_PATH,
    _TEXT_FONT_PATH,
    _draw_centered,
    _draw_icon,
    _load_font,
)

WIDTH = 400
HEIGHT = 300

# Header band holds the date (left) and the current HH:MM (right).
HEADER_H = 42
# Two equal day rows fill the area below the header.
ROW_TOP_1 = HEADER_H
ROW_SEP_Y = HEADER_H + (HEIGHT - HEADER_H) // 2  # 171
ROW_TOP_2 = ROW_SEP_Y

COLS = 8  # 8 three-hourly slots per day row
COL_W = WIDTH // COLS  # 50

# Vertical offsets within a day row, relative to the row's top edge.
_DAY_LABEL_Y = 4
_HOUR_LABEL_Y = 26
_ICON_BOX_TOP = 40
_ICON_BOX_BOTTOM = 92
_TEMP_Y = 96

DATE_FONT = _load_font(_TEXT_FONT_PATH, 18)
TIME_FONT = _load_font(_TEXT_FONT_PATH, 30)
DAY_FONT = _load_font(_TEXT_FONT_PATH, 15)
LABEL_FONT = _load_font(_TEXT_FONT_PATH, 12)
TEMP_FONT = _load_font(_TEXT_FONT_PATH, 15)
PAGE_ICON_FONT = _load_font(_ICON_FONT_PATH, 30)
MSG_FONT = _load_font(_TEXT_FONT_PATH, 16)


def _day_label(dt, now):
    """Short label for a day row, relative to the current day."""
    delta = (dt.date() - now.date()).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    return dt.strftime("%a %-d %b")


def _draw_header(draw, now):
    draw.text((6, 11), now.strftime("%a %-d %b %Y"), font=DATE_FONT, fill=0)
    time_str = now.strftime("%H:%M")
    w = draw.textlength(time_str, font=TIME_FONT)
    draw.text((WIDTH - 6 - w, 5), time_str, font=TIME_FONT, fill=0)
    draw.line((0, HEADER_H, WIDTH - 1, HEADER_H), fill=0, width=2)


def _draw_day_row(draw, row_top, day_slots, now):
    """Draw one day's worth of 3-hourly forecast cells."""
    draw.text((6, row_top + _DAY_LABEL_Y), _day_label(day_slots[0]["dt"], now),
              font=DAY_FONT, fill=0)
    for c, slot in enumerate(day_slots):
        cx = c * COL_W + COL_W // 2
        temp = slot["temp"]
        temp_str = f"{round(temp):d}°" if temp is not None else "--°"
        _draw_centered(draw, f"{slot['hour']:02d}h", LABEL_FONT, cx,
                       row_top + _HOUR_LABEL_Y)
        _draw_icon(draw, slot["glyph"], PAGE_ICON_FONT, cx,
                   row_top + _ICON_BOX_TOP, row_top + _ICON_BOX_BOTTOM)
        _draw_centered(draw, temp_str, TEMP_FONT, cx, row_top + _TEMP_Y)


def render_weather_page(slots, now):
    """Render the full-page forecast to a 1-bit PIL image.

    slots: list from weather.fetch_weather_2day(), or None when unavailable.
    now: timezone-aware datetime for the header date/time and day labels.
    """
    canvas = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(canvas)

    _draw_header(draw, now)

    if not slots:
        _draw_centered(draw, "Weather unavailable", MSG_FONT, WIDTH // 2,
                       HEADER_H + (HEIGHT - HEADER_H) // 2 - 8)
    else:
        # Split into two day rows of COLS cells each.
        _draw_day_row(draw, ROW_TOP_1, slots[:COLS], now)
        if len(slots) > COLS:
            draw.line((0, ROW_SEP_Y, WIDTH - 1, ROW_SEP_Y), fill=0, width=1)
            _draw_day_row(draw, ROW_TOP_2, slots[COLS:COLS * 2], now)

    return canvas.convert("1", dither=Image.Dither.NONE)


if __name__ == "__main__":
    # Render a sample using live weather (falls back to the unavailable page)
    # for quick visual inspection.
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from weather import TIMEZONE, fetch_weather_2day

    sample_now = datetime.now(ZoneInfo(TIMEZONE))
    img = render_weather_page(fetch_weather_2day(), sample_now)
    out = "weather_page_sample.png"
    img.save(out)
    print(f"Wrote {out}")
