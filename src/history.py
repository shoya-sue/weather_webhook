"""履歴管理モジュール"""

import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import List


@dataclass
class NotificationRecord:
    """通知記録"""
    date: str  # "2026-01-09"
    location_id: str  # "tokyo_hq"
    notification_type: str  # "rain"
    sent_at: str  # ISO形式タイムスタンプ


@dataclass
class NotificationHistory:
    """通知履歴"""
    records: List[NotificationRecord] = field(default_factory=list)

    def was_notified_today(
        self,
        location_id: str,
        notification_type: str,
        target_date: date
    ) -> bool:
        """
        指定日にすでに通知済みかを判定

        Args:
            location_id: 拠点ID
            notification_type: 通知タイプ（"rain", "typhoon", "warning"）
            target_date: 対象日

        Returns:
            True: 通知済み
            False: 未通知
        """
        target_date_str = target_date.strftime("%Y-%m-%d")

        for record in self.records:
            if (record.date == target_date_str and
                record.location_id == location_id and
                    record.notification_type == notification_type):
                return True

        return False

    def add_record(
        self,
        location_id: str,
        notification_type: str,
        target_date: date
    ) -> None:
        """
        通知記録を追加

        Args:
            location_id: 拠点ID
            notification_type: 通知タイプ
            target_date: 対象日
        """
        record = NotificationRecord(
            date=target_date.strftime("%Y-%m-%d"),
            location_id=location_id,
            notification_type=notification_type,
            sent_at=datetime.now().isoformat()
        )
        self.records.append(record)

    def cleanup_old_records(self, keep_days: int = 7) -> None:
        """
        古い記録を削除

        Args:
            keep_days: 保持する日数
        """
        today = date.today()
        cutoff_date = today.strftime("%Y-%m-%d")

        # keep_days日以内の記録のみ保持
        new_records = []
        for record in self.records:
            try:
                record_date = datetime.strptime(record.date, "%Y-%m-%d").date()
                days_diff = (today - record_date).days
                if days_diff <= keep_days:
                    new_records.append(record)
            except ValueError:
                # 日付パースに失敗した場合は削除
                pass

        self.records = new_records


def load_history(file_path: Path) -> NotificationHistory:
    """
    履歴ファイルを読み込む

    Args:
        file_path: 履歴ファイルのパス

    Returns:
        NotificationHistory: 通知履歴（ファイルがなければ空の履歴）
    """
    if not file_path.exists():
        return NotificationHistory()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        # 読み込みに失敗した場合は空の履歴を返す
        return NotificationHistory()

    records = []
    for record_data in data.get("records", []):
        try:
            records.append(NotificationRecord(
                date=record_data["date"],
                location_id=record_data["location_id"],
                notification_type=record_data["notification_type"],
                sent_at=record_data["sent_at"]
            ))
        except (KeyError, TypeError):
            # 不正なレコードはスキップ
            continue

    return NotificationHistory(records=records)


def save_history(history: NotificationHistory, file_path: Path) -> None:
    """
    履歴ファイルを保存

    Args:
        history: 通知履歴
        file_path: 保存先パス
    """
    data = {
        "records": [asdict(record) for record in history.records]
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
