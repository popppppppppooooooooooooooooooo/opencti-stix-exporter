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
import logging
from concurrent.futures import ThreadPoolExecutor
from stix2 import Relationship, Sighting

# region init
# =====================
# init IN
# =====================

ssl_verify = True

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
    global clientb
    # OpenCTI APIクライアントの初期化
    clienta = OpenCTIApiClient(url, token, ssl_verify=ssl_verify)
    clientb = clienta
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
            spin.start()
            while pagination_data["pagination"]["hasNextPage"]:
                
                cursor = pagination_data.get("pagination", {}).get("endCursor")
                params = {}
                print(f"cursor: {str(cursor)}")
                spin.stop()
                if cursor is not None:
                    params["after"] = cursor
                
                # エンティティタイプを指定しない全件取得
                data = self.client.stix_domain_object.list(
                    filters=filter_query,
                    first=page_size,
                    withPagination=True,
                    **params
                )
                spin.start()
                                
                all_entities.extend(data['entities'])
                pagination_data = data
                
                # デバッグ用ログ出力
                # cursor = pagination_data.get("pagination", {}).get("endCursor")
                
            spin.stop()
        
        except Exception as e:
            self.logger.error(f"エンティティ取得エラー: {str(e)}")
            raise
        
        return convert_to_stix(all_entities, clientb)
        # return all_entities

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
                
                spin.stop()
                all_relationships.extend(data['entities'])
                
                pagination_data = data


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
    stix_objects = []
    converter = OpenCTIStix2(client)
    
    if data is None:
        print("##### data is None #####")
        return []
    if "entity_type" not in str(data):
        print("##### entity_type not found #####")
        return []
    
    for rel in tqdm(data):
        entity_type = rel.get('entity_type')

        if entity_type == 'stix-core-relationship':
            stix_obj = client.stix_core_relationship.to_stix2(entity=rel, mode="full")
            stix_objects.apend(stix_obj)

        if entity_type == 'stix-sighting-relationship':
            stix_obj = client.stix_sighting_relationship.to_stix2(entity=rel, mode="full")
            stix_objects.apend(stix_obj)

        if entity_type == 'stix-nested-ref-relationship':
            stix_obj = client.stix_nested_ref_relationship.to_stix2(entity=rel, mode="full")
            stix_objects.apend(stix_obj)

        else:
            stix_objects.append(converter.generate_export(entity=rel))
            # tqdm.write("WARN:unknown type <" + entity_type + "> skipped")
        
    return stix_objects

# region bundle
def make_stix_bundle(stix_obj):

    stix_bundle = {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid4()}",
        "objects": stix_obj
        }
    return stix_bundle


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
        # stix_objects = convert_to_stix(all_entities, client)
        stix_objects = make_stix_bundle(all_entities)
        
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
    OpenCTIのリレーションシップオブジェクトリストをSTIX2.1形式のオブジェクトリストに変換する。
    
    :param client: OpenCTIApiClient インスタンス（OpenCTI APIクライアント）
    :param relationships: リレーションシップオブジェクトのリスト
    :return: STIX2.1形式（辞書）のオブジェクトリスト
    """
    # キャッシュ：内部IDからstandard_id（STIX ID）へのマッピングを保持
    id_cache = {}

    def get_standard_id(internal_id, type_hint=None):
        """OpenCTI内部IDからSTIX標準IDを取得する（必要に応じてAPIを呼び出す）。"""
        if not internal_id:
            return None
        # すでに取得済みならキャッシュを返す
        if internal_id in id_cache:
            return id_cache[internal_id]
        try:
            obj_data = None
            # オブジェクト種別に応じて適切な読み出しメソッドを呼ぶ
            if type_hint:
                # Identity系
                identity_types = {"Individual", "Organization", "Sector", "System"}
                location_types = {"Country", "City", "Region", "Position"}
                if type_hint in identity_types or type_hint == "Identity":
                    obj_data = client.identity.read(id=internal_id)
                elif type_hint in location_types or type_hint == "Location":
                    obj_data = client.location.read(id=internal_id)
                # サイバーオブザーバブル（SCO）
                elif "-" in type_hint and type_hint.lower() != type_hint:  # 大文字含むハイフン表記
                    # STIX Cyber Observableの場合（例: IPv4-Addr 等）
                    # OpenCTIでは汎用的に stix_cyber_observable で取得
                    obj_data = client.stix_cyber_observable.read(id=internal_id)
                else:
                    # STIXドメインオブジェクト（SDO）と判断
                    # クライアントの属性名に合わせて小文字・アンダースコアに変換
                    attr = type_hint.lower().replace("-", "_")
                    if hasattr(client, attr):
                        obj_data = getattr(client, attr).read(id=internal_id)
                    else:
                        # 属性がない場合は汎用読み出しを試みる
                        try:
                            obj_data = client.stix_domain_object.read(id=internal_id)
                        except Exception:
                            obj_data = client.stix_cyber_observable.read(id=internal_id)
            else:
                # type_hintがない場合は汎用的に取得を試みる
                try:
                    obj_data = client.stix_domain_object.read(id=internal_id)
                except Exception:
                    obj_data = client.stix_cyber_observable.read(id=internal_id)
            # 成功した場合、standard_idをキャッシュ
            if obj_data:
                stix_id = obj_data.get("standard_id") or obj_data.get("id")
                if stix_id:
                    id_cache[internal_id] = stix_id
                    return stix_id
        except Exception as e:
            logging.warning(f"Failed to fetch object {internal_id}: {e}")
        return None

    def convert_relationship(rel):
        """単一のリレーションシップオブジェクトをSTIX2.1形式に変換する。"""
        try:
            # リレーションシップ種別の判定
            # OpenCTIのentity_typeやtypeで判別（sightingか否か）
            etype = rel.get("entity_type") or rel.get("type") or ""
            # Sighting関係の処理
            if etype.lower().endswith("sighting-relationship") or etype.lower() == "sighting":
                stix_obj = {
                    "type": "sighting",
                    "spec_version": "2.1"
                }
                # STIX IDの設定
                stix_obj["id"] = rel.get("standard_id") or rel.get("id") or get_standard_id(rel.get("id"))
                # sighting_of_ref: 目撃対象（source側）のID
                # OpenCTIでは通常、from側が目撃対象
                source_id = rel.get("from") or rel.get("fromId")
                source_type = rel.get("fromType") or (source_id.get("entity_type") if isinstance(source_id, dict) else None)
                # source_idがオブジェクトの場合はそのstandard_idを直接利用、無ければ内部IDから取得
                if isinstance(source_id, dict):
                    sighting_of = source_id.get("standard_id") or source_id.get("id")
                else:
                    sighting_of = get_standard_id(source_id, source_type)
                stix_obj["sighting_of_ref"] = sighting_of
                # where_sighted_refs: 目撃した主体（target側）のIDリスト
                target_id = rel.get("to") or rel.get("toId")
                target_type = rel.get("toType") or (target_id.get("entity_type") if isinstance(target_id, dict) else None)
                if target_id:
                    if isinstance(target_id, dict):
                        where_id = target_id.get("standard_id") or target_id.get("id")
                    else:
                        where_id = get_standard_id(target_id, target_type)
                    if where_id:
                        stix_obj["where_sighted_refs"] = [where_id]
                # 時間・回数プロパティの設定
                if rel.get("first_seen"):
                    stix_obj["first_seen"] = rel["first_seen"]
                if rel.get("last_seen"):
                    stix_obj["last_seen"] = rel["last_seen"]
                # OpenCTIではsightingの回数をattribute_countとして持つ場合がある
                count = rel.get("attribute_count") or rel.get("count")
                if count is not None:
                    stix_obj["count"] = count
                # その他任意プロパティの設定
                if rel.get("description"):
                    stix_obj["description"] = rel["description"]
                if rel.get("confidence") is not None:
                    stix_obj["confidence"] = rel["confidence"]
                # OpenCTI拡張フィールド: 負の目撃情報フラグなど
                if rel.get("x_opencti_negative") is not None:
                    stix_obj["x_opencti_negative"] = rel["x_opencti_negative"]
                # 作成日時・修正日時の設定（無い場合はスキップ）
                created = rel.get("created") or rel.get("created_at")
                modified = rel.get("modified") or rel.get("updated_at")
                if created:
                    stix_obj["created"] = created
                if modified:
                    stix_obj["modified"] = modified if modified else created
                # 作成者とマーキングの参照設定
                if rel.get("createdBy") or rel.get("createdById"):
                    creator = rel.get("createdBy")
                    if isinstance(creator, dict):
                        stix_obj["created_by_ref"] = creator.get("standard_id") or creator.get("id")
                    else:
                        # internal IDから取得
                        cb_id = rel.get("createdById")
                        if cb_id:
                            stix_obj["created_by_ref"] = get_standard_id(cb_id)
                if rel.get("objectMarking") or rel.get("objectMarkingIds"):
                    marks = rel.get("objectMarking") or []
                    marking_ids = []
                    if isinstance(marks, list) and marks:
                        # オブジェクトのリストの場合
                        for m in marks:
                            if isinstance(m, dict):
                                marking_ids.append(m.get("standard_id") or m.get("id"))
                            else:
                                marking_ids.append(m)
                    elif rel.get("objectMarkingIds"):
                        marking_ids = rel["objectMarkingIds"]
                    if marking_ids:
                        stix_obj["object_marking_refs"] = []
                        for mid in marking_ids:
                            # マーキング定義もキャッシュ/取得
                            md_stix_id = get_standard_id(mid, "MarkingDefinition")
                            if md_stix_id:
                                stix_obj["object_marking_refs"].append(md_stix_id)
                return stix_obj

            # 通常のリレーションシップ（stix-core-relationship）の処理
            stix_obj = {
                "type": "relationship",
                "spec_version": "2.1"
            }
            stix_obj["id"] = rel.get("standard_id") or rel.get("id") or get_standard_id(rel.get("id"))
            # relationship_type（必須）
            stix_obj["relationship_type"] = rel.get("relationship_type") or rel.get("type")  # 一部のデータでは'type'に関係種別が入る場合も対応
            # source_refとtarget_refを決定
            src_obj = rel.get("from") or rel.get("source") or rel.get("src")  # 'source'や'src'キーの可能性も考慮
            tgt_obj = rel.get("to") or rel.get("target") or rel.get("tgt")
            src_type = rel.get("fromType") or (src_obj.get("entity_type") if isinstance(src_obj, dict) else None)
            tgt_type = rel.get("toType") or (tgt_obj.get("entity_type") if isinstance(tgt_obj, dict) else None)
            # ソース参照
            if src_obj:
                if isinstance(src_obj, dict):
                    source_id = src_obj.get("standard_id") or src_obj.get("id")
                else:
                    source_id = get_standard_id(src_obj, src_type)
                stix_obj["source_ref"] = source_id
            # ターゲット参照
            if tgt_obj:
                if isinstance(tgt_obj, dict):
                    target_id = tgt_obj.get("standard_id") or tgt_obj.get("id")
                else:
                    target_id = get_standard_id(tgt_obj, tgt_type)
                stix_obj["target_ref"] = target_id
            # 任意プロパティ（説明、期間、信頼度など）
            if rel.get("description"):
                stix_obj["description"] = rel["description"]
            # 時間範囲：OpenCTIのfirst_seen/last_seenはSTIX関係ではstart_time/stop_timeに相当
            if rel.get("first_seen") or rel.get("start_time"):
                stix_obj["start_time"] = rel.get("start_time") or rel.get("first_seen")
            if rel.get("last_seen") or rel.get("stop_time"):
                stix_obj["stop_time"] = rel.get("stop_time") or rel.get("last_seen")
            if rel.get("confidence") is not None:
                stix_obj["confidence"] = rel["confidence"]
            # 作成日時・修正日時
            created = rel.get("created") or rel.get("created_at")
            modified = rel.get("modified") or rel.get("updated_at")
            if created:
                stix_obj["created"] = created
            if modified:
                stix_obj["modified"] = modified if modified else created
            # 作成者の参照
            if rel.get("createdBy") or rel.get("createdById"):
                creator = rel.get("createdBy")
                if isinstance(creator, dict):
                    stix_obj["created_by_ref"] = creator.get("standard_id") or creator.get("id")
                else:
                    cb_id = rel.get("createdById")
                    if cb_id:
                        stix_obj["created_by_ref"] = get_standard_id(cb_id)
            # マーキング定義の参照一覧
            if rel.get("objectMarking") or rel.get("objectMarkingIds"):
                marks = rel.get("objectMarking") or []
                marking_ids = []
                if isinstance(marks, list) and marks:
                    for m in marks:
                        if isinstance(m, dict):
                            marking_ids.append(m.get("standard_id") or m.get("id"))
                        else:
                            marking_ids.append(m)
                elif rel.get("objectMarkingIds"):
                    marking_ids = rel["objectMarkingIds"]
                if marking_ids:
                    stix_obj["object_marking_refs"] = []
                    for mid in marking_ids:
                        md_stix_id = get_standard_id(mid, "MarkingDefinition")
                        if md_stix_id:
                            stix_obj["object_marking_refs"].append(md_stix_id)
            return stix_obj
        except Exception as e:
            # エラー発生時は警告ログを出力してNoneを返す
            rel_id = rel.get("id") or rel.get("standard_id") or str(rel)
            logging.warning(f"Failed to process relationship {rel_id}: {e}")
            return None

    # リレーションシップリストを並列処理で変換
    stix_objects = []
    if relationships:
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(convert_relationship, rel): rel for rel in relationships}
            for future in futures:
                rel = futures[future]
                try:
                    obj = future.result()
                    if obj:
                        stix_objects.append(obj)
                except Exception as e:
                    rel_id = rel.get("id") or rel.get("standard_id") or str(rel)
                    logging.warning(f"Error in processing relationship {rel_id}: {e}")
    return stix_objects

# region debug
def debug(target=""):
    if target == "":
        print("##############################")
        print("debug information")
        print("==============================")
        print(url)
        print(token)
        print(output_path)
        print("ssl_verify:"+str(ssl_verify))
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