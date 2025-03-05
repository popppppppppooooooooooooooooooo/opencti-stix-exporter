#! /usr/bin/python3

# ========== SPINNER_START START ==========
print("starting " + __file__);from halo import Halo;spin = Halo(text='wait a moment...', spinner='dots');spin.start() # spin.stop()
# ========== SPINNER_START END ==========


from pycti import OpenCTIApiClient
from pycti.utils.opencti_stix2 import OpenCTIStix2
import json
from datetime import datetime, timedelta
from stix2 import MemoryStore, Filter
from tqdm import tqdm
from halo import Halo
import logging
from typing import List, Optional, Dict
import time
from stix2 import Identity, parse
import uuid, re

# region init
# =====================
# init IN
# =====================


# read setting.json
with open('setting.json', 'r', encoding='utf-8-sig') as f:
    settings = json.load(f)
    url = settings['opencti']['url']
    token = settings['opencti']['token']
    
    end_date = datetime(settings['start_date'][0], settings['start_date'][1], settings['start_date'][2], settings['start_date'][3], settings['start_date'][4], settings['start_date'][5])
    start_date = datetime(settings['end_date'][0], settings['end_date'][1], settings['end_date'][2], settings['end_date'][3], settings['end_date'][4], settings['end_date'][5])
    output_path = settings['output_path']


# OpenCTIの接続設定
# url = "http://hoge:25000"
# token = "deadbeef-fafa-fefe-fafa-deadbeefdead"

# 日時範囲の設定（例：過去24時間）
# end_date = datetime.now()
# start_date = end_date - timedelta(hours=24)
# end_date = datetime(2026, 1, 1, 0, 0, 0)
# start_date = datetime(2024, 1, 1, 0, 0, 0)
# output_path = "stix.json"


# =====================
# init OUT
# =====================

# region main
def main():
    # OpenCTI APIクライアントの初期化
    clienta = OpenCTIApiClient(url, token)
    client = SecureEntityClient(clienta)

    # entitycount = client.get_entity_count(def_filter(start_date, end_date))

    relations = client.get_filtered_relationship(def_filter(start_date, end_date))
    export_filtered_entities(clienta, relations, sanitize_windows_filename(str(end_date) + "_relations_"), output_path)

    entityes = client.get_all_stix_entities(def_filter(start_date, end_date))
    export_filtered_entities(clienta, entityes, sanitize_windows_filename(str(end_date) + "_entities_"), output_path)

    print(f"{len(entityes)}個のエンティティーが出力されました")
    print(f"{len(relations)}個のリレーションが出力されました")

#region filter
def def_filter(start_date, end_date):
    # Filter = "modified >= {} AND modified <= {}".format(start_date.isoformat(), end_date.isoformat())
    Filter = {
        "mode": "and",
        "filters": [
                {
                    "key": "modified",
                    "values": [format(start_date.isoformat())],
                    "operator": "gte",
                    "mode": "or"
                },
                {
                    "key": "modified",
                    "values": [format(end_date.isoformat())],
                    "operator": "lte",
                    "mode": "or"
                }
            ],
        "filterGroups": []
        }
    return Filter

# region class
class SecureEntityClient:
    def __init__(self, client: OpenCTIApiClient):
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.max_retries = 3
        self.retry_delay = 1  # 秒単位

    #region entity
    def get_all_stix_entities(self, filter_query=None, page_size=100):
        """
        STIX形式のエンティティを全件取得する関数
        
        Args:
            filter_query (dict): フィルタリング条件（オプション）
            page_size (int): ページネーションのページサイズ（デフォルト: 100）
        
        Returns:
            dict: STIX形式のエンティティ一覧を含む辞書
            
        Raises:
            Exception: API呼び出しでエラーが発生した場合
        """
        all_entities = []
        pagination_data = {
            "pagination": {"hasNextPage": True, "endCursor": None},
            "filters": filter_query,
            "filterGroups": []
        }
        


        try:
            while pagination_data["pagination"]["hasNextPage"]:
                cursor = pagination_data.get("pagination", {}).get("endCursor")
                params = {}
                
                if cursor is not None:
                    params["after"] = cursor
                
                # エンティティタイプを指定しない全件取得
                data = self.client.stix_domain_object.list(
                    filters=filter_query,
                    first=page_size,
                    withPagination=True,
                    **params
                )
                
                all_entities.extend(data['entities'])
                pagination_data = data
                
                # デバッグ用ログ出力
                cursor = pagination_data.get("pagination", {}).get("endCursor")
                print(f"cursor: {str(cursor)}")
        
        except Exception as e:
            self.logger.error(f"エンティティ取得エラー: {str(e)}")
            raise
        
        return all_entities

    #region rerationship
    def get_filtered_relationship(self, filter_query, page_size=100):
        all_entities = []
        pagination_data = {
            "pagination": {"hasNextPage": True, "endCursor": None},
            "filters": filter_query,
            "filterGroups": []
        }


        try:
            while pagination_data["pagination"]["hasNextPage"]:
                """DOC_STRING HERE""";"""
                # エンティティタイプごとに適切なメソッドを使用
                if filter_query.get('type') == 'ThreatActor':
                    data = self.client.threat_actor.list(
                        filters=filter_query,
                        first=page_size,
                        withPagination=True
                    )
                elif filter_query.get('type') == 'Incident':
                    data = self.client.incident.list(
                        filters=filter_query,
                        first=page_size,
                        withPagination=True
                    )
                else:
                複数のエンティティタイプを取得する場合
                """
                cursor = pagination_data.get("pagination", {}).get("endCursor")
                params = {}

                if cursor is not None:
                    params["after"] = cursor

                data = self.client.stix_core_relationship.list(
                    filters=filter_query,
                    first=page_size,
                    withPagination=True,
                    after=cursor
                )
                
                all_entities.extend(data['entities'])

                print(f"cursor: {str(cursor)}")
                pagination_data = data

            return all_entities

        except Exception as e:
            self.logger.error(f"リレーション取得エラー: {str(e)}")
            raise

    def get_entity_count(self, filter_query: List[Dict]) -> int:
        """
        フィルタリングされたエンティティの総数を取得
        
        :param filter_query: フィルタリングクエリ文字列
        :return: エンティティの総数
        """
        return None
        try:
            data = self.client.stix_core_relationship.list(
                filters=filter_query,
                max_remote_objects=0,
                with_pagination=True
            )
            return data.get('total', 0)
        except Exception as e:
            self.logger.error(f"エンティティ数取得エラー: {str(e)}")
            raise

# region convert
def convert_to_stix(data, client):
    converter = OpenCTIStix2(client)

    if data is None:
        print("##### data is None #####")
        return []
    if "entity_type" not in str(data):
        print("##### entity_type not found #####")
        return []

    stix = []
    for item in tqdm(data):
        stix.append(converter.generate_export(entity=item))
    
    # manifest = {
    # "type": "x-opencti-manifest",
    # "name": f"OpenCTI Export {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    # "version": "1.0",
    # "objects": []
    # }

    stix_bundle = {
    "type": "bundle",
    "id": f"bundle--{uuid.uuid4()}",
    "objects": stix
    }
    
    return stix_bundle
    # """辞書データまたはリストデータをSTIX Identityオブジェクトに変換"""
    # stix_objects = []
    
    # # data が辞書かリストかを判定
    # if isinstance(data, dict):
    #     entities = data.get("data", [])
    # elif isinstance(data, list):
    #     entities = data
    # else:
    #     raise TypeError("データの形式が不正です。辞書またはリストを渡してください。")

    # for item in entities:
    #     if not isinstance(item, dict):
    #         continue  # アイテムが辞書でない場合はスキップ
        
    #     stix_identity = Identity(
    #         id=item.get("standard_id", "identity--unknown"),
    #         type="identity",
    #         name=item.get("name", "Unknown"),
    #         description=item.get("description", "No description"),
    #         identity_class="sector",
    #         confidence=item.get("confidence", 0),
    #         created=item.get("created", "1970-01-01T00:00:00.000Z"),
    #         modified=item.get("modified", "1970-01-01T00:00:00.000Z")
    #     )
    #     stix_objects.append(stix_identity)

    # return stix_objects

# region export
def export_filtered_entities(client, all_entities, filename, output_path):
    # print(str(all_entities))
    print(f"{len(all_entities)}件の書き込み中")
    # ファイル出力

    # STIXオブジェクトに変換
    stix_objects = convert_to_stix(all_entities, client)
    # 各 STIX オブジェクトを辞書形式に変換
    # stix_dicts = [obj.to_dict() for obj in stix_objects]
    with open(filename + output_path, 'w', encoding='utf-8') as f:
        json.dump(stix_objects, f, ensure_ascii=False, indent=2)

def sanitize_windows_filename(filename):
    """
    Windowsファイル名から無効な文字を除去する関数
    セキュリティ上の考慮事項：
    - バックスラッシュはエスケープシーケンスとして扱われるため特別な処理が必要
    - 正規表現パターンのコンパイルは一度だけ行い、キャッシュすることで性能を最適化
    """
    # 無効な文字の正規表現パターンをコンパイル
    invalid_chars_pattern = re.compile(r'[\/:*?"<>|\\\+]')  # \+ は正規表現での特殊文字
    
    # ファイル名をサニタイズ
    sanitized_name = invalid_chars_pattern.sub('_', str(filename))
    
    return sanitized_name

# region debug
def debug(target=""):
    if target == "":
        print("##############################")
        print("debug information")
        print("==============================")
        print(url)
        print(token)
        print(output_path)
        print("==============================")
        print(start_date)
        print(end_date)
        print("==============================")
        print(def_filter(start_date, end_date))
        print("##############################")


# ========== SPINNER_STOP START ==========
spin.stop()
# ========== SPINNER_STOP END ==========


if __name__ == "__main__":
    debug()
    main()