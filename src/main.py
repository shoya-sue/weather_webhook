#!/usr/bin/env python3
"""天気通知Bot メインエントリーポイント"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_config, ConfigError
from weather import (
    fetch_weather_xml,
    parse_weather_xml,
    check_rain_alert,
    check_weather_alert,
    WeatherAPIError,
    WeatherParseError
)
from history import load_history, save_history
from notifier import (
    format_rain_message,
    format_weather_message,
    send_slack_notification,
    NotificationError
)


# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description="天気通知Bot - 雨の可能性がある場合にSlackに通知"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="通知を送信せず、結果を標準出力に表示"
    )
    parser.add_argument(
        "--config",
        default="config/settings.json",
        help="設定ファイルのパス (デフォルト: config/settings.json)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="履歴に関係なく強制的に通知判定を行う"
    )
    return parser.parse_args()


def main() -> int:
    """
    メイン処理

    Returns:
        0: 成功（通知なしも含む）
        1: エラー
    """
    args = parse_args()
    today = date.today()

    logger.info("処理開始")

    # 設定読み込み
    try:
        config = load_config(args.config)
        logger.info(f"設定読み込み完了: {len(config.locations)}拠点")
    except ConfigError as e:
        logger.error(f"設定エラー: {e}")
        return 1

    # 雨通知が無効の場合はスキップ
    if not config.rain_notify.enabled:
        logger.info("雨通知は無効に設定されています")
        return 0

    # 履歴読み込み
    history_path = Path(config.history_file_path)
    history = load_history(history_path)
    logger.info(f"履歴読み込み完了: {len(history.records)}件")

    # 古い履歴をクリーンアップ
    history.cleanup_old_records(keep_days=7)

    notifications_sent = 0
    notifications_skipped = 0

    for location in config.locations:
        logger.info(f"天気情報取得: {location.name}")

        # 天気情報取得
        try:
            xml_content = fetch_weather_xml(location.prefecture_id)
        except WeatherAPIError as e:
            logger.error(f"  天気API取得エラー: {e}")
            continue

        # XML解析
        try:
            forecast = parse_weather_xml(xml_content, location.area_id)
        except WeatherParseError as e:
            logger.warning(f"  XML解析エラー: {e}")
            continue

        # 降水確率ログ出力
        rainfall_str = ", ".join([
            f"{p.hour_range}={p.probability}%"
            for p in forecast.rainfall_periods
        ])
        logger.info(f"  降水確率: {rainfall_str}")
        logger.info(f"  天気詳細: {forecast.weather_detail}")

        # 雨判定（通知済みでなければ）
        rain_alert = None
        if not args.force and history.was_notified_today(location.id, "rain", today):
            logger.info(f"  {location.name}: 雨通知は本日送信済み")
        else:
            rain_alert = check_rain_alert(
                forecast,
                config.rain_notify.threshold,
                location.name
            )
            if rain_alert is None:
                logger.info(f"  {location.name}: 降水確率が閾値({config.rain_notify.threshold}%)未満")

        # 特殊天気判定（通知済みでなければ）
        weather_alert = None
        if not args.force and history.was_notified_today(location.id, "weather", today):
            logger.info(f"  {location.name}: 特殊天気通知は本日送信済み")
        else:
            weather_alert = check_weather_alert(forecast, location.name)
            if weather_alert:
                logger.info(f"  {location.name}: 特殊天気検出: {weather_alert.detected_conditions}")
            else:
                logger.info(f"  {location.name}: 特殊天気なし")

        # 通知が不要な場合はスキップ
        if rain_alert is None and weather_alert is None:
            continue

        # 雨通知メッセージ送信
        if rain_alert:
            message = format_rain_message(rain_alert)
            if args.dry_run:
                logger.info(f"  [DRY-RUN] 雨通知メッセージ:")
                print("-" * 40)
                print(message)
                print("-" * 40)
            else:
                try:
                    send_slack_notification(config.slack_webhook_url, message)
                    logger.info(f"  {location.name}: 雨通知送信完了")
                    history.add_record(location.id, "rain", today)
                    notifications_sent += 1
                except NotificationError as e:
                    logger.error(f"  Slack通知エラー: {e}")
                    return 1

        # 特殊天気通知メッセージ送信
        if weather_alert:
            message = format_weather_message(weather_alert)
            if args.dry_run:
                logger.info(f"  [DRY-RUN] 特殊天気通知メッセージ:")
                print("-" * 40)
                print(message)
                print("-" * 40)
            else:
                try:
                    send_slack_notification(config.slack_webhook_url, message)
                    logger.info(f"  {location.name}: 特殊天気通知送信完了")
                    history.add_record(location.id, "weather", today)
                    notifications_sent += 1
                except NotificationError as e:
                    logger.error(f"  Slack通知エラー: {e}")
                    return 1

    # 履歴保存
    if not args.dry_run and notifications_sent > 0:
        try:
            save_history(history, history_path)
            logger.info("履歴更新完了")
        except IOError as e:
            logger.warning(f"履歴保存エラー: {e}")

    logger.info(f"処理終了: 通知送信={notifications_sent}, スキップ={notifications_skipped}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
