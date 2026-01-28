"""天気情報取得・解析モジュール"""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


class WeatherAPIError(Exception):
    """天気API関連エラー"""
    pass


class WeatherParseError(Exception):
    """XML解析エラー"""
    pass


@dataclass
class RainfallPeriod:
    """時間帯別降水確率"""
    hour_range: str  # "00-06", "06-12", "12-18", "18-24"
    probability: int  # 0-100


@dataclass
class WeatherForecast:
    """天気予報データ"""
    prefecture: str
    area: str
    date: str
    weather: str
    weather_detail: str
    temp_max: Optional[int]
    temp_min: Optional[int]
    rainfall_periods: List[RainfallPeriod]


@dataclass
class RainAlert:
    """雨通知データ"""
    location_name: str
    area: str
    date: str
    alert_periods: List[RainfallPeriod]  # 閾値以上の時間帯


@dataclass
class WeatherAlert:
    """特殊天気通知データ（雷・雪・みぞれ等）"""
    location_name: str
    area: str
    date: str
    weather_detail: str
    detected_conditions: List[str]  # 検出された天気条件


def fetch_weather_xml(
    prefecture_id: str,
    timeout: int = 10,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> str:
    """
    drk7から天気XMLを取得

    Args:
        prefecture_id: 都道府県ID（例: "13" for 東京）
        timeout: タイムアウト秒数
        max_retries: 最大リトライ回数
        retry_delay: リトライ間隔（秒）

    Returns:
        XML文字列

    Raises:
        WeatherAPIError: API取得に失敗した場合
    """
    url = f"https://www.drk7.jp/weather/xml/{prefecture_id}.xml"

    last_error = None
    for attempt in range(max_retries):
        try:
            with urlopen(url, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

    raise WeatherAPIError(f"天気情報の取得に失敗しました: {last_error}")


def _parse_rainfall_probability(value: str) -> int:
    """
    降水確率を数値に変換

    Args:
        value: 降水確率の文字列（"30", "-" など）

    Returns:
        降水確率（0-100）。ハイフンの場合は0
    """
    if value == "-" or value == "":
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def parse_weather_xml(xml_content: str, area_id: str) -> WeatherForecast:
    """
    XMLを解析して天気予報データを返す

    Args:
        xml_content: XML文字列
        area_id: エリアID（例: "東京地方"）

    Returns:
        WeatherForecast: 天気予報データ

    Raises:
        WeatherParseError: XML解析に失敗した場合
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise WeatherParseError(f"XMLの解析に失敗しました: {e}")

    # prefを探す
    pref_elem = root.find(".//pref")
    if pref_elem is None:
        raise WeatherParseError("pref要素が見つかりません")

    prefecture = pref_elem.get("id", "")

    # 指定されたareaを探す
    area_elem = None
    for area in pref_elem.findall("area"):
        if area.get("id") == area_id:
            area_elem = area
            break

    if area_elem is None:
        raise WeatherParseError(f"指定されたエリアが見つかりません: {area_id}")

    # 当日の天気情報（最初のinfo）を取得
    info_elem = area_elem.find("info")
    if info_elem is None:
        raise WeatherParseError("info要素が見つかりません")

    date = info_elem.get("date", "")
    weather = info_elem.findtext("weather", "")
    weather_detail = info_elem.findtext("weather_detail", "")

    # 気温
    temp_max = None
    temp_min = None
    temperature = info_elem.find("temperature")
    if temperature is not None:
        for range_elem in temperature.findall("range"):
            centigrade = range_elem.get("centigrade")
            try:
                value = int(range_elem.text) if range_elem.text else None
                if centigrade == "max":
                    temp_max = value
                elif centigrade == "min":
                    temp_min = value
            except (ValueError, TypeError):
                pass

    # 降水確率
    rainfall_periods = []
    rainfallchance = info_elem.find("rainfallchance")
    if rainfallchance is not None:
        for period in rainfallchance.findall("period"):
            hour_range = period.get("hour", "")
            probability = _parse_rainfall_probability(period.text or "")
            rainfall_periods.append(RainfallPeriod(
                hour_range=hour_range,
                probability=probability
            ))

    return WeatherForecast(
        prefecture=prefecture,
        area=area_id,
        date=date,
        weather=weather,
        weather_detail=weather_detail,
        temp_max=temp_max,
        temp_min=temp_min,
        rainfall_periods=rainfall_periods
    )


# 特殊天気のキーワードと表示名
WEATHER_KEYWORDS = {
    "雷": "雷",
    "雪": "雪",
    "みぞれ": "みぞれ",
    "霙": "みぞれ",
    "あられ": "あられ",
    "霰": "あられ",
    "ひょう": "ひょう",
    "雹": "ひょう",
    "暴風": "暴風",
    "大雨": "大雨",
    "大雪": "大雪",
}


def check_rain_alert(
    forecast: WeatherForecast,
    threshold: int,
    location_name: str
) -> Optional[RainAlert]:
    """
    降水確率が閾値以上の時間帯があるかチェック

    Args:
        forecast: 天気予報データ
        threshold: 閾値（%）
        location_name: 表示用の拠点名

    Returns:
        RainAlert: 閾値以上の時間帯がある場合
        None: 閾値以上の時間帯がない場合
    """
    alert_periods = [
        p for p in forecast.rainfall_periods
        if p.probability >= threshold
    ]

    if not alert_periods:
        return None

    return RainAlert(
        location_name=location_name,
        area=forecast.area,
        date=forecast.date,
        alert_periods=alert_periods
    )


def check_weather_alert(
    forecast: WeatherForecast,
    location_name: str,
    keywords: Optional[List[str]] = None
) -> Optional[WeatherAlert]:
    """
    特殊な天気条件（雷・雪・みぞれ等）をチェック

    Args:
        forecast: 天気予報データ
        location_name: 表示用の拠点名
        keywords: 検出するキーワードリスト（Noneの場合はデフォルト）

    Returns:
        WeatherAlert: 特殊天気が検出された場合
        None: 特殊天気がない場合
    """
    if keywords is None:
        keywords = list(WEATHER_KEYWORDS.keys())

    # weather_detailから特殊天気を検出
    detail = forecast.weather_detail
    detected = []

    for keyword in keywords:
        if keyword in detail:
            display_name = WEATHER_KEYWORDS.get(keyword, keyword)
            if display_name not in detected:
                detected.append(display_name)

    if not detected:
        return None

    return WeatherAlert(
        location_name=location_name,
        area=forecast.area,
        date=forecast.date,
        weather_detail=detail,
        detected_conditions=detected
    )
