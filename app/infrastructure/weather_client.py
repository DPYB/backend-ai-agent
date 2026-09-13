"""Open-Meteo free weather client with graceful fallback (Zero-cost, no API key required)."""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# WMO Weather interpretation codes (WW)
WMO_WEATHER_MAP = {
    0: "맑음(쾌청한 하늘)",
    1: "대체로 맑음",
    2: "구름 조금",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "가벼운 이슬비",
    53: "보통 이슬비",
    55: "짙은 이슬비",
    61: "약한 비",
    63: "보통 비",
    65: "강한 비",
    71: "약한 눈",
    73: "보통 눈",
    75: "강한 눈",
    77: "싸락눈",
    80: "약한 소나기",
    81: "보통 소나기",
    82: "격렬한 소나기",
    85: "약한 눈 소나기",
    86: "강한 눈 소나기",
    95: "뇌우(천둥번개)",
    96: "우박을 동반한 약한 뇌우",
    99: "우박을 동반한 강한 뇌우",
}


class WeatherClient:
    """Client for fetching live current weather by coordinates using Open-Meteo free API."""

    def __init__(self, timeout: float = 2.5):
        self.timeout = timeout
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    async def get_current_weather(self, latitude: float, longitude: float) -> Optional[str]:
        """Fetch current weather description and temperature for given latitude and longitude.

        Returns human-readable Korean weather summary (e.g. '보통 비, 기온 18.5°C') or None.
        """
        try:
            params: dict[str, Any] = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    current = data.get("current", {})
                    weather_code = current.get("weather_code")
                    temp = current.get("temperature_2m")

                    weather_desc = WMO_WEATHER_MAP.get(weather_code, "맑음")
                    summary = f"{weather_desc}"
                    if temp is not None:
                        summary += f", 기온 {temp}°C"
                    logger.info(
                        "Fetched live weather for (lat=%s, lon=%s): %s",
                        latitude,
                        longitude,
                        summary,
                    )
                    return summary
        except Exception as e:
            logger.warning(
                "Failed to fetch weather from Open-Meteo (%s). Continuing without live weather.", e
            )
        return None


_weather_client: Optional[WeatherClient] = None


def get_weather_client() -> WeatherClient:
    """Return singleton WeatherClient instance."""
    global _weather_client
    if _weather_client is None:
        _weather_client = WeatherClient()
    return _weather_client
