# main.py の README

## 概要

`main.py` は、OpenCTI プラットフォームから STIX データをエクスポートするためのスクリプトです。このスクリプトを使用することで、OpenCTI 内の脅威インテリジェンスデータを STIX 形式で取得し、他のシステムと共有することができます。

## 必要条件

- Python 3.6 以上
- OpenCTI API キー
<!-- - 必要な Python ライブラリ（requirements.txt に記載） -->

## インストール

1. リポジトリをクローンします。

    ```bash
    git clone https://github.com/yourusername/opencti-stix-exporter.git
    cd opencti-stix-exporter
    ```

2. 必要なライブラリをインストールします。
<!-- 
    ```bash
    pip install -r requirements.txt
    ```
 -->
## 使い方

1. `config.json` ファイルを編集し、OpenCTI API キーとエンドポイントを設定します。

    ```json
    {
        "opencti": {
            "url": "https://your-opencti-instance.com",
            "token": "your_api_key"
        }
    }
    ```

2. スクリプトを実行します。

    ```bash
    python main.py
    ```

3. エクスポートされた STIX データは、指定された出力ディレクトリに保存されます。

## ライセンス

このプロジェクトは GPL ライセンスの下で公開されています。詳細は `LICENSE` ファイルを参照してください。

## 貢献

バグ報告や機能リクエストは、GitHub の Issue トラッカーを使用してください。プルリクエストも歓迎します。

