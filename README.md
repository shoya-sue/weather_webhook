# 天気通知Bot

雨の可能性がある場合のみSlackに通知する「静かなBot」です。

## 機能

- 降水確率が40%以上の時間帯がある場合にSlack通知
- 1日1回（朝7:00 JST）の自動実行
- 重複通知の防止

## セットアップ

### 1. リポジトリのSecrets設定

GitHub リポジトリの Settings > Secrets and variables > Actions で以下を設定:

| Secret名 | 説明 |
|----------|------|
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

### 2. Slack Incoming Webhookの取得

1. [Slack API](https://api.slack.com/apps) にアクセス
2. アプリを作成（または既存アプリを選択）
3. 「Incoming Webhooks」を有効化
4. 「Add New Webhook to Workspace」でチャンネルを選択
5. 生成されたWebhook URLをコピー

### 3. 監視地点の設定（オプション）

`config/settings.json` を編集して監視地点を変更:

```json
{
  "locations": [
    {
      "id": "tokyo_hq",
      "name": "本社（東京）",
      "prefecture_id": "13",
      "area_id": "東京地方"
    }
  ],
  "rain_notify": {
    "enabled": true,
    "threshold": 40
  }
}
```

## ローカル実行

```bash
# 環境変数を設定
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/xxx/yyy/zzz"

# dry-runモード（通知を送信しない）
python src/main.py --dry-run

# 通常実行
python src/main.py
```

## 手動実行（GitHub Actions）

1. リポジトリの「Actions」タブを開く
2. 「Weather Notification」を選択
3. 「Run workflow」をクリック

## 都道府県ID一覧

| ID | 都道府県 | ID | 都道府県 |
|----|----------|----|---------|
| 1 | 北海道 | 13 | 東京都 |
| 2 | 青森県 | 14 | 神奈川県 |
| 3 | 岩手県 | 27 | 大阪府 |
| 4 | 宮城県 | 40 | 福岡県 |

※ 全都道府県ID: 1-47

## 通知例

```
:umbrella_with_rain_drops: 本社（東京）- 雨の可能性があります

:round_pushpin: 東京地方の降水確率
+----------+------+
|  時間帯  | 確率 |
+----------+------+
| 06-12時  |  50% |
| 12-18時  |  60% |
+----------+------+

傘をお忘れなく！
```
