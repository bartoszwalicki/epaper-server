import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = 52.4064
LONGITUDE = 16.9252

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
    """Fetch next two hourly forecasts for the configured location.

    Returns a list of two dicts (offset_hours, temp, code, glyph) on success,
    or None on any failure so the caller can skip the overlay.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m,weather_code",
        "forecast_hours": 3,
        "timezone": "Europe/Warsaw",
    }
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=3)
        response.raise_for_status()
        hourly = response.json()["hourly"]
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]
        # forecast_hours=3 yields [current, +1h, +2h] in order.
        return [
            {
                "offset_hours": offset,
                "temp": temps[idx],
                "code": codes[idx],
                "glyph": WMO_GLYPH.get(codes[idx], FALLBACK_GLYPH),
            }
            for offset, idx in ((1, 1), (2, 2))
        ]
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None
