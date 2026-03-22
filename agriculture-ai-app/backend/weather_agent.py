import os
from pathlib import Path
from typing import Dict, Union

import requests
from dotenv import load_dotenv

# Load workspace-level .env regardless of execution CWD.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _get_openweather_api_key() -> str:
    return (
        os.getenv("OPENWEATHER_API_KEY")
        or os.getenv("WEATHER_API_KEY")
        or "YOUR_OPENWEATHER_API_KEY"
    )


def get_weather_by_pincode(pincode: str) -> Dict[str, Union[float, str]]:
    """Fetch weather from OpenWeather API given Indian PIN.

    Uses zip-based query: zip={pin},IN
    """

    api_key = _get_openweather_api_key()
    if not api_key or api_key == "YOUR_OPENWEATHER_API_KEY":
        return {"error": "OpenWeather API key not configured on server."}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"zip": f"{pincode},IN", "appid": api_key, "units": "metric"}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"Failed to fetch weather: {e}"}

    main = data.get("main", {})
    wind = data.get("wind", {})
    weather_list = data.get("weather", [])
    weather_desc = weather_list[0]["description"] if weather_list else "Unknown"

    rain = 0.0
    rain_obj = data.get("rain") or {}
    if "1h" in rain_obj:
        rain = float(rain_obj["1h"])
    elif "3h" in rain_obj:
        rain = float(rain_obj["3h"])

    return {
        "temperature": float(main.get("temp", 0.0)),
        "humidity": float(main.get("humidity", 0.0)),
        "wind_speed": float(wind.get("speed", 0.0)),
        "rain": rain,
        "description": weather_desc.title(),
        "place_name": data.get("name") or "",
    }


def get_weather_by_coords(lat: float, lon: float) -> Dict[str, Union[float, str]]:
    """Fetch weather from OpenWeather API given latitude/longitude.

    Used by the drone monitoring map when a user clicks on a field location.
    """

    api_key = _get_openweather_api_key()
    if not api_key or api_key == "YOUR_OPENWEATHER_API_KEY":
        return {"error": "OpenWeather API key not configured on server."}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"Failed to fetch weather: {e}"}

    main = data.get("main", {})
    wind = data.get("wind", {})
    weather_list = data.get("weather", [])
    weather_desc = weather_list[0]["description"] if weather_list else "Unknown"

    rain = 0.0
    rain_obj = data.get("rain") or {}
    if "1h" in rain_obj:
        rain = float(rain_obj["1h"])
    elif "3h" in rain_obj:
        rain = float(rain_obj["3h"])

    return {
        "temperature": float(main.get("temp", 0.0)),
        "humidity": float(main.get("humidity", 0.0)),
        "wind_speed": float(wind.get("speed", 0.0)),
        "rain": rain,
        "description": weather_desc.title(),
        "place_name": data.get("name") or "",
    }


def build_farming_suggestion(weather: Dict[str, Union[float, str]]) -> str:
    t = float(weather.get("temperature", 0.0))
    h = float(weather.get("humidity", 0.0))
    r = float(weather.get("rain", 0.0))

    suggestions = []

    if r > 2:
        suggestions.append("Rain expected – reduce irrigation and ensure drainage.")
    else:
        suggestions.append("No major rain – plan irrigation as per crop stage.")

    if h > 80:
        suggestions.append("High humidity – monitor for fungal diseases (blight, mildew).")

    if t >= 35:
        suggestions.append("Heat stress – use mulching and evening irrigation where possible.")
    elif t <= 18:
        suggestions.append("Cool conditions – choose tolerant varieties and avoid waterlogging.")

    if not suggestions:
        return "Conditions look normal for most field crops."

    return " ".join(suggestions)
