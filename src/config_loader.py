"""設定読み込みモジュール"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


class ConfigError(Exception):
    """設定読み込みエラー"""
    pass


@dataclass
class LocationConfig:
    """拠点設定"""
    id: str
    name: str
    prefecture_id: str
    area_id: str


@dataclass
class RainNotifyConfig:
    """雨通知設定"""
    enabled: bool
    threshold: int


@dataclass
class AppConfig:
    """アプリケーション設定"""
    locations: List[LocationConfig]
    rain_notify: RainNotifyConfig
    slack_webhook_url: str
    history_file_path: str


def load_config(
    config_path: str = "config/settings.json",
    env_webhook_key: str = "SLACK_WEBHOOK_URL",
    env_history_key: str = "HISTORY_FILE_PATH"
) -> AppConfig:
    """
    設定を読み込む

    Args:
        config_path: 設定ファイルのパス
        env_webhook_key: Webhook URLの環境変数名
        env_history_key: 履歴ファイルパスの環境変数名

    Returns:
        AppConfig: アプリケーション設定

    Raises:
        ConfigError: 設定読み込みに失敗した場合
    """
    # 設定ファイル読み込み
    config_file = Path(config_path)
    if not config_file.exists():
        raise ConfigError(f"設定ファイルが見つかりません: {config_path}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"設定ファイルのJSON解析に失敗: {e}")

    # locations の検証と変換
    if "locations" not in data or not data["locations"]:
        raise ConfigError("設定に locations が必要です")

    locations = []
    for loc in data["locations"]:
        required_keys = ["id", "name", "prefecture_id", "area_id"]
        missing = [k for k in required_keys if k not in loc]
        if missing:
            raise ConfigError(f"location に必須キーがありません: {missing}")

        locations.append(LocationConfig(
            id=loc["id"],
            name=loc["name"],
            prefecture_id=str(loc["prefecture_id"]),
            area_id=loc["area_id"]
        ))

    # rain_notify の検証と変換
    rain_data = data.get("rain_notify", {})
    rain_notify = RainNotifyConfig(
        enabled=rain_data.get("enabled", True),
        threshold=rain_data.get("threshold", 40)
    )

    # 環境変数から取得
    slack_webhook_url = os.environ.get(env_webhook_key, "")
    if not slack_webhook_url:
        raise ConfigError(f"環境変数 {env_webhook_key} が設定されていません")

    history_file_path = os.environ.get(env_history_key, "history.json")

    return AppConfig(
        locations=locations,
        rain_notify=rain_notify,
        slack_webhook_url=slack_webhook_url,
        history_file_path=history_file_path
    )
