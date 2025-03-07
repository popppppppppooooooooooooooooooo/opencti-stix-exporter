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
import os

# region init
# =====================
# init IN
# =====================


# read setting.json
with open('setting.json', 'r', encoding='utf-8-sig') as f:
    settings = json.load(f)
    url = settings['opencti']['url']
    token = settings['opencti']['token']
    
    start_date = datetime(settings['start_date'][0], settings['start_date'][1], settings['start_date'][2], settings['start_date'][3], settings['start_date'][4], settings['start_date'][5])
    end_date = datetime(settings['end_date'][0], settings['end_date'][1], settings['end_date'][2], settings['end_date'][3], settings['end_date'][4], settings['end_date'][5])
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

    # export_filtered_entities(clienta, relations, sanitize_windows_filename(str(end_date) + "_relations_"), output_path)


    entityes = client.get_all_stix_entities(def_filter(start_date, end_date))
    # export_filtered_entities(clienta, entityes, sanitize_windows_filename(str(end_date) + "_entities_"), ou   tput_path)

    objects = entityes + relations

    export_filtered_entities(clienta, objects, sanitize_windows_filename(str(end_date) + "_all_"), output_path)

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
    def get_all_stix_entities(self, filter_query=None, page_size=5000):
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
                print(f"cursor: {str(cursor)}")
                spin.start()
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
                # cursor = pagination_data.get("pagination", {}).get("endCursor")
                
                spin.stop()
        
        except Exception as e:
            self.logger.error(f"エンティティ取得エラー: {str(e)}")
            raise
        
        return all_entities

    #region rerationship
    def get_filtered_relationship(self, filter_query, page_size=5000, container_id=None):
        """
        フィルタ条件に合致するリレーションシップ（SRO）を全件取得し、
        オプションで指定されたコンテナ（例：Report）の object_refs にも追加する関数

        Args:
            filter_query (dict): フィルタリング条件
            page_size (int): ページネーションのページサイズ（デフォルト: 100）
            container_id (str, optional): 関連付け対象のコンテナID（例：ReportのID）

        Returns:
            list: 取得したリレーションシップオブジェクトのリスト

        Raises:
            Exception: API呼び出しでエラーが発生した場合
        """
        all_relationships = []
        pagination_data = {
            "pagination": {"hasNextPage": True, "endCursor": None},
            "filters": filter_query,
            "filterGroups": []
        }

        try:
            while pagination_data["pagination"]["hasNextPage"]:
                cursor = pagination_data.get("pagination", {}).get("endCursor")
                params = {"after": cursor} if cursor is not None else {}
                print(f"cursor: {str(cursor)}")
                spin.start()
                # エンティティタイプごとに適切なメソッドを使用する例（必要に応じて追加）
                if filter_query.get('type') == 'ThreatActor':
                    data = self.client.threat_actor.list(
                        filters=filter_query,
                        first=page_size,
                        withPagination=True,
                        **params
                    )
                elif filter_query.get('type') == 'Incident':
                    data = self.client.incident.list(
                        filters=filter_query,
                        first=page_size,
                        withPagination=True,
                        **params
                    )
                else:
                    # 通常はリレーションシップ用のメソッドを使用する
                    data = self.client.stix_core_relationship.list(
                        filters=filter_query,
                        first=page_size,
                        withPagination=True,
                        **params
                    )

                all_relationships.extend(data['entities'])
                
                pagination_data = data
                spin.stop()

            # コンテナIDが指定されている場合、各リレーションのIDをコンテナの object_refs に追加する
            if container_id:
                container = self.client.report.read(id=container_id)
                current_refs = container.get("object_refs", [])
                for rel in all_relationships:
                    if rel["id"] not in current_refs:
                        self.client.report.add_stix_object_or_stix_relationship(
                            id=container_id,
                            stixObjectOrStixRelationshipId=rel["id"]
                        )
            return process_relationships_and_update_containers(all_relationships, self.client, filter_query, page_size)

        except Exception as e:
            self.logger.error(f"リレーション取得エラー: {str(e)}")
            raise

    # region count
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
    """
    STIX形式への変換関数
    セキュリティ対策：
    - データ型チェックの強化
    - エラー処理の改善
    - ロギング機能の追加
    """
    converter = OpenCTIStix2(client)
    stix_objects = []
    
    def validate_entity(entity):
        """エンティティの検証関数"""
        # if not isinstance(entity, dict):
        #     raise ValueError(f"無効なエンティティ形式: {type(entity)}")
        # if "entity_type" not in entity:
        #     raise KeyError("エンティティタイプが存在しません")
        
    try:
        # 単一のエンティティ処理
        if isinstance(data, dict):
            validate_entity(data)
            stix_object = converter.generate_export(entity=data)
            if stix_object:
                stix_objects.append(stix_object)
                
        # 複数エンティティ（リスト）の処理
        elif isinstance(data, list):
            for item in data:
                try:
                    validate_entity(item)
                    stix_object = converter.generate_export(entity=item)
                    if stix_object:
                        stix_objects.append(stix_object)
                except Exception as e:
                    logging.error(f"エンティティ変換エラー: {str(e)}")
                    
        return {
            "type": "bundle",
            "id": f"bundle--{uuid.uuid4()}",
            "objects": stix_objects,
            "spec_version": "2.1"
        }
        
    except Exception as e:
        logging.error(f"STIX変換プロセス全体でエラー発生: {str(e)}")
        raise

# region export
def export_filtered_entities(client, all_entities, filename, output_path):
    """
    エンティティのフィルタリングと出力
    セキュリティ対策：
    - 入力値検証
    - ファイル操作の安全性確保
    """
    if not isinstance(all_entities, (list, tuple)):
        raise TypeError("all_entitiesはリストまたはタプルである必要があります")
    
    print(f"{len(all_entities)}件の書き込み中")
    
    try:
        # STIXオブジェクトに変換
        stix_objects = convert_to_stix(all_entities, client)
        
        # ファイル出力
        sanitized_filename = sanitize_windows_filename(filename)
        # file_path = os.path.join(output_path, sanitized_filename)
        file_path = filename + output_path
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(stix_objects, f, ensure_ascii=False, indent=2)
            
        return True
        
    except Exception as e:
        logging.error(f"エンティティ出力エラー: {str(e)}")
        return False


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

# region process
def process_relationships_and_update_containers(relationships, client, filter_query, page_size):
    """
    渡されたリレーションシップのリストから、各リレーションに含まれるコンテナIDを取得し、
    そのコンテナのobject_refsに、リレーションのsource_refおよびtarget_refを追加したローカルの
    コンテナオブジェクトのリストと、元のリレーションシップのリストを返す関数。
    
    Args:
        relationships (list): リレーションシップオブジェクトのリスト（辞書形式）
        client: pyctiのインスタンス（APIクライアント）
        filter_query (dict): フィルター条件（ここでは主に情報として受け取る）
        page_size (int): ページネーションサイズ（この関数内では使用しない）
    
    Returns:
        tuple: (updated_containers, relationships)
            updated_containers: 各コンテナ（例：Report）のobject_refsに対象エンティティが追加されたローカルコピーのリスト
            relationships: 入力されたリレーションシップのリスト
    """
    # コンテナのローカルコピーをIDで保持する辞書
    containers = {}
    
    # すべてのリレーションシップを処理
    for rel in tqdm(relationships):
        # 各リレーションからコンテナIDを取得（ここでは "container_id" というキーを想定）
        container_id = rel.get("container_id")
        if not container_id:
            continue  # コンテナIDがない場合はスキップ
        
        # コンテナがまだ取得されていなければ、API経由で読み込み（ローカルコピーとして保持）
        if container_id not in containers:
            container = client.report.read(id=container_id)
            if container is None:
                continue  # 読み込みに失敗した場合はスキップ
            # object_refsが存在しなければ初期化
            if "object_refs" not in container or container["object_refs"] is None:
                container["object_refs"] = []
            containers[container_id] = container
        
        # リレーションのsource_refとtarget_refを取得して、重複なくコンテナのobject_refsに追加
        for ref in [rel.get("source_ref"), rel.get("target_ref")]:
            if ref and ref not in containers[container_id]["object_refs"]:
                containers[container_id]["object_refs"].append(ref)
    
    # ローカルに更新したコンテナのリストと、元のリレーションシップリストを返す
    return list(containers.values()) + list(relationships)

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
exit()