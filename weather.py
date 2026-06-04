from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = 52.4064
LONGITUDE = 16.9252
TIMEZONE = "Europe/Warsaw"

# Used only when the timezone database is unavailable (e.g. a minimal Alpine or
# slim image without tzdata) AND no API offset is on hand. Europe/Warsaw is +2
# in summer (CEST); this may be 1h off in winter, but it only affects the rare
# "weather unavailable" page, never the live forecast (which carries its own
# DST-aware offset from Open-Meteo).
FALLBACK_UTC_OFFSET = timedelta(hours=2)


def local_now(offset_seconds=None):
    """Current wall-clock time at the configured location, tz-aware.

    Prefers the DST-aware offset returned by Open-Meteo so the server needs no
    timezone database. Falls back to the system tz database, then to a fixed
    offset, so it never raises even on an image without tzdata.
    """
    if offset_seconds is not None:
        return datetime.now(timezone.utc).astimezone(
            timezone(timedelta(seconds=offset_seconds)))
    try:
        return datetime.now(ZoneInfo(TIMEZONE))
    except Exception:
        return datetime.now(timezone(FALLBACK_UTC_OFFSET))

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

    Returns a list of two dicts (hour, temp, code, glyph) on success, or None on
    any failure so the caller can skip the overlay. "hour" is the local clock
    hour (0-23) of the forecast, e.g. 16 for the +2h slot when it is ~14:xx.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weather_code",
        "forecast_hours": 6,
        "timezone": TIMEZONE,
    }
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=3)
        response.raise_for_status()
        hourly = response.json()["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]
        # forecast_hours=6 yields [current, +1h, +2h, +3h, +4h, +5h] in order,
        # so the +2h and +5h forecasts are at indices 2 and 5. The timestamps
        # are local (timezone above), so dt.hour is the local clock hour.
        return [
            {
                "hour": datetime.fromisoformat(times[idx]).hour,
                "temp": temps[idx],
                "code": codes[idx],
                "glyph": WMO_GLYPH.get(codes[idx], FALLBACK_GLYPH),
            }
            for idx in (2, 5)
        ]
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None


# Number of 3-hourly slots shown on the full-page forecast: 2 days x 8 slots.
FORECAST_SLOTS = 16
SLOT_STEP_HOURS = 3


def fetch_weather_2day():
    """Fetch a rolling 2-day forecast sampled every 3 hours.

    Returns a dict {"slots", "offset_seconds"} where "slots" is up to
    FORECAST_SLOTS dicts (dt, hour, temp, code, glyph) starting at the next
    3-hour clock boundary at or after the current local time, and
    "offset_seconds" is the location's DST-aware UTC offset. Returns None on any
    failure so the caller can render a "weather unavailable" page.
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
        data = response.json()
        hourly = data["hourly"]
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]
        offset_seconds = data.get("utc_offset_seconds", 0)

        # Open-Meteo returns naive ISO timestamps already in the requested
        # timezone. Derive a naive "now" in that same zone from the API's
        # DST-aware offset, so the server needs no local timezone database.
        now_local = local_now(offset_seconds).replace(tzinfo=None)

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
        if not slots:
            return None
        return {"slots": slots, "offset_seconds": offset_seconds}
    except Exception as e:
        print(f"Error fetching 2-day weather: {e}")
        return None
