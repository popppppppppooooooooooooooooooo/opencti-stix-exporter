# OpenCTI STIX Exporter

このプロジェクトは、OpenCTIからSTIX形式のデータをエクスポートするためのツールです。指定された日時範囲内のエンティティとリレーションシップを取得し、STIX 2.1形式で出力します。

## 必要条件

- Python 3.x
- 必要なPythonパッケージ（requirements.txtに記載）

<!-- ## インストール

1. リポジトリをクローンします。

    ```bash
    git clone https://github.com/yourusername/opencti-stix-exporter.git
    cd opencti-stix-exporter
    ```

2. 必要なPythonパッケージをインストールします。

    ```bash
    pip install -r requirements.txt
    ``` -->

## 設定

`setting.json`ファイルを編集して、OpenCTIのURL、APIトークン、データの取得範囲、出力ファイルパスを設定します。

```json
{
    "opencti": {
        "url": "http://your-opencti-url",
        "token": "your-api-token"
    },
    "start_date": [2025, 1, 1, 0, 0, 0],
    "end_date": [2025, 1, 7, 0, 0, 0],
    "output_path": "stix.json"
}
```

### 設定パラメーターの説明

- `opencti.url`: OpenCTIのインスタンスのURLを指定します。
- `opencti.token`: APIトークンを指定します。これにより、OpenCTIのAPIにアクセスするための認証が行われます。
- `start_date`: データ取得の開始日時を指定します。形式は `[年, 月, 日, 時, 分, 秒]` です。
- `end_date`: データ取得の終了日時を指定します。形式は `[年, 月, 日, 時, 分, 秒]` です。
- `output_path`: 取得したデータを保存するファイルのパスを指定します。

## 使い方

1. スクリプトを実行します。

    ```bash
    python3 main.py
    ```

2. 指定された日時範囲内のエンティティとリレーションシップが取得され、STIX形式で出力されます。

## デバッグ

デバッグ情報を表示するには、`main.py`の最後にある`debug()`関数を呼び出します。

```python
if __name__ == "__main__":
    debug()
    main()
```

## スクリプトの構成

- `main.py`: メインスクリプト。OpenCTI APIクライアントの初期化、データの取得、STIX形式への変換、ファイル出力を行います。
- `setting.json`: 設定ファイル。OpenCTIのURL、APIトークン、データの取得範囲、出力ファイルパスを指定します。

## 注意事項

- `setting.json`ファイルには、APIトークンなどの機密情報が含まれます。適切に管理してください。
- 出力ファイルのパスには、無効な文字が含まれないようにしてください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細はLICENSEファイルを参照してください。