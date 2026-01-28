"""Slack通知モジュール"""

import json
import time
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from weather import RainAlert, RainfallPeriod, WeatherAlert


class NotificationError(Exception):
    """通知送信エラー"""
    pass


def _format_rainfall_table(periods: List[RainfallPeriod]) -> str:
    """
    降水確率をテーブル形式にフォーマット

    Args:
        periods: 降水確率の時間帯リスト

    Returns:
        テーブル形式の文字列
    """
    lines = []
    lines.append("```")
    lines.append("+----------+------+")
    lines.append("|  時間帯  | 確率 |")
    lines.append("+----------+------+")

    for period in periods:
        # 時間帯を表示用に整形（例: "06-12" -> "06-12時"）
        hour_display = f"{period.hour_range}時"
        prob_display = f"{period.probability}%"

        # 幅を揃える
        lines.append(f"| {hour_display:^8} | {prob_display:>4} |")

    lines.append("+----------+------+")
    lines.append("```")

    return "\n".join(lines)


def format_rain_message(alert: RainAlert) -> str:
    """
    雨通知メッセージを整形

    Args:
        alert: 雨通知データ

    Returns:
        整形されたメッセージ
    """
    lines = []

    # ヘッダー
    lines.append(f":umbrella_with_rain_drops: {alert.location_name} - 雨の可能性があります")
    lines.append("")

    # エリアと降水確率テーブル
    lines.append(f":round_pushpin: {alert.area}の降水確率")
    lines.append(_format_rainfall_table(alert.alert_periods))

    # フッター
    lines.append("")
    lines.append("傘をお忘れなく！")

    return "\n".join(lines)


# 天気条件ごとの絵文字マッピング
WEATHER_EMOJI = {
    "雷": ":zap:",
    "雪": ":snowflake:",
    "みぞれ": ":cloud_with_snow:",
    "あられ": ":cloud_with_snow:",
    "ひょう": ":cloud_with_snow:",
    "暴風": ":dash:",
    "大雨": ":rain_cloud:",
    "大雪": ":snowflake:",
}


def format_weather_message(alert: WeatherAlert) -> str:
    """
    特殊天気通知メッセージを整形

    Args:
        alert: 特殊天気通知データ

    Returns:
        整形されたメッセージ
    """
    lines = []

    # 絵文字を決定（最初に見つかった条件の絵文字を使用）
    emoji = ":warning:"
    for condition in alert.detected_conditions:
        if condition in WEATHER_EMOJI:
            emoji = WEATHER_EMOJI[condition]
            break

    # 検出された条件を連結
    conditions_str = "・".join(alert.detected_conditions)

    # ヘッダー
    lines.append(f"{emoji} {alert.location_name} - {conditions_str}の予報")
    lines.append("")

    # 詳細
    lines.append(f":round_pushpin: {alert.area}")
    lines.append(f"```{alert.weather_detail}```")

    # フッター
    lines.append("")
    lines.append("お出かけの際はご注意ください。")

    return "\n".join(lines)


def send_slack_notification(
    webhook_url: str,
    message: str,
    timeout: int = 10,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> bool:
    """
    Slackに通知を送信

    Args:
        webhook_url: Incoming Webhook URL
        message: 送信するメッセージ
        timeout: タイムアウト秒数
        max_retries: 最大リトライ回数
        retry_delay: リトライ間隔（秒）

    Returns:
        True: 送信成功
        False: 送信失敗

    Raises:
        NotificationError: 送信に失敗した場合
    """
    payload = {
        "text": message
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json"
    }

    request = Request(
        webhook_url,
        data=data,
        headers=headers,
        method="POST"
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                if response.status == 200:
                    return True
        except (HTTPError, URLError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))

    raise NotificationError(f"Slack通知の送信に失敗しました: {last_error}")
