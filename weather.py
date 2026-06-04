from datetime import datetime
from zoneinfo import ZoneInfo

import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = 52.4064
LONGITUDE = 16.9252
TIMEZONE = "Europe/Warsaw"

# WMO weather code 4677 (Open-Meteo) → Erik Flowers Weather Icons codepoint.
# See: https://open-meteo.com/en/docs (WMO Weather interpretation codes)
# Codepoints sourced from weather-icons/sass/icon-variables/*.scss.
WMO_GLYPH = {
    0:  "",  # day-sunny: Clear sky
    1:  "",  # day-cloudy: Mainly clear
    2:  "",  # day-cloudy: Partly cloudy
    3:  "",  # cloudy: Overcast
    45: "",  # fog
    48: "",  # fog: Depositing rime fog
    51: "",  # sprinkle: Drizzle light
    53: "",  # sprinkle: Drizzle moderate
    55: "",  # sprinkle: Drizzle dense
    56: "",  # sprinkle: Freezing drizzle light
    57: "",  # sprinkle: Freezing drizzle dense
    61: "",  # rain: Rain slight
    63: "",  # rain: Rain moderate
    65: "",  # rain: Rain heavy
    66: "",  # rain: Freezing rain light
    67: "",  # rain: Freezing rain heavy
    71: "",  # snow: Snow fall slight
    73: "",  # snow: Snow fall moderate
    75: "",  # snow: Snow fall heavy
    77: "",  # snow: Snow grains
    80: "",  # showers: Rain showers slight
    81: "",  # showers: Rain showers moderate
    82: "",  # showers: Rain showers violent
    85: "",  # snow: Snow showers slight
    86: "",  # snow: Snow showers heavy
    95: "",  # thunderstorm
    96: "",  # thunderstorm with slight hail
    99: "",  # thunderstorm with heavy hail
}

FALLBACK_GLYPH = ""  # cloudy


def fetch_weather():
    """Fetch the +2h and +5h hourly forecasts for the configured location.

    Returns a list of two dicts (offset_hours, temp, code, glyph) on success,
    or None on any failure so the caller can skip the overlay.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weather_code",
        "forecast_hours": 6,
        "timezone": "Europe/Warsaw",
    }
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=3)
        response.raise_for_status()
        hourly = response.json()["hourly"]
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]
        # forecast_hours=6 yields [current, +1h, +2h, +3h, +4h, +5h] in order,
        # so the +2h and +5h forecasts are at indices 2 and 5.
        return [
            {
                "offset_hours": offset,
                "temp": temps[idx],
                "code": codes[idx],
                "glyph": WMO_GLYPH.get(codes[idx], FALLBACK_GLYPH),
            }
            for offset, idx in ((2, 2), (5, 5))
        ]
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None


# Number of 3-hourly slots shown on the full-page forecast: 2 days x 8 slots.
FORECAST_SLOTS = 16
SLOT_STEP_HOURS = 3


def fetch_weather_2day():
    """Fetch a rolling 2-day forecast sampled every 3 hours.

    Returns a list of FORECAST_SLOTS dicts (dt, hour, temp, code, glyph) starting
    at the next 3-hour clock boundary at or after the current local time, or None
    on any failure so the caller can render a "weather unavailable" page.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weather_code",
        # 3 days so a rolling 48h window started late in the day still has
        # enough hours past midnight to fill all FORECAST_SLOTS.
        "forecast_days": 3,
        "timezone": TIMEZONE,
    }
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=3)
        response.raise_for_status()
        hourly = response.json()["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]

        # Open-Meteo returns naive ISO timestamps already in the requested
        # timezone, so compare against a naive "now" in the same zone.
        now_local = datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)

        # Pick the timestamps that land on a 3-hour clock boundary (00,03,...)
        # at or after now. Selecting by the local wall-clock hour (rather than
        # stepping a fixed number of array indices) keeps the slots on the
        # 3-hour grid even across DST transitions, where a local day has 23 or
        # 25 hourly entries.
        slots = []
        for t, temp, code in zip(times, temps, codes):
            dt = datetime.fromisoformat(t)
            if dt < now_local or dt.hour % SLOT_STEP_HOURS != 0:
                continue
            slots.append({
                "dt": dt,
                "hour": dt.hour,
                "temp": temp,  # may be None; the renderer shows "--"
                "code": code,
                "glyph": WMO_GLYPH.get(code, FALLBACK_GLYPH),
            })
            if len(slots) >= FORECAST_SLOTS:
                break
        return slots if slots else None
    except Exception as e:
        print(f"Error fetching 2-day weather: {e}")
        return None
