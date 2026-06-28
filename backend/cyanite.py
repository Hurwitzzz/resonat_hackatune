"""基础设施 · Cyanite REST 封装。全项目唯一碰网络的地方。

编排层只调这里的函数；测试时 monkeypatch 本模块即可离线跑。
REST 形态取自 notebooks/cyanite_model_outputs.ipynb 与 guides/ 里的官方 PDF。

四个官方端点 ↔ 本模块函数：
  #1 GET  /v1/library-tracks/{id}/models            -> model_tags()      (tagging)
  #2 POST /v1/private-alpha/library-tracks/search   -> search_by_prompt() (prompt 搜索)
  #3 POST /v1/private-alpha/library-tracks/{id}/similar -> find_similar()  (单种子)
  #4 POST /v1/private-alpha/library-tracks/similar  -> find_similar_multi() (≤10 种子)
"""
from __future__ import annotations
import csv
import json
import pathlib

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import config

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
_DATA = _DATA_DIR / "tracks.csv"
_MAPPER = _DATA_DIR / "jamendo_mapper.json"

# 数据包 CSV：~1 万首"口味种子"曲的真实展示信息（含 artist），启动时载入一次。
_JAM_TO_CYAN: dict[str, str] = {}
_DISPLAY: dict[str, dict] = {}
with _DATA.open() as f:
    for row in csv.DictReader(f):
        _JAM_TO_CYAN[row["track_id"]] = row["cyanite_id"]
        _DISPLAY[row["cyanite_id"]] = {
            "track_id": row["track_id"],
            "cyanite_id": row["cyanite_id"],
            "title": row.get("name", ""),
            "artist": row.get("artist_name", ""),
        }
_CYAN_TO_JAM = {c: j for j, c in _JAM_TO_CYAN.items()}

# 全库映射 cyanite_id -> jamendo track_id（~357k）。search/similar 会返回整个 catalog 的曲，
# 不只数据包那 1 万首；没有这个映射，非种子曲就拿不到 track_id（→ 无法播放、卡片空白）。
# ponytail: 30MB JSON 全量载入内存（~30MB 常驻）。曲库不再变，省事最划算；真嫌占内存再换 sqlite/lazy。
_CYAN_TO_TRACK: dict[str, str] = {}
with _MAPPER.open() as f:
    for cid, info in json.load(f).items():
        _CYAN_TO_TRACK[cid] = str(info.get("jamendo_title", "")).split(".mp3")[0]

# 共享限流退避：Cyanite 有共享 rate limit，explain 扇出会成倍打它。429/5xx 自动退避重试，
# 听服务端 Retry-After；用尽才抛。覆盖全部 4 个端点。
_session = requests.Session()
_session.headers.update({"x-api-key": config.CYANITE_API_KEY})
_retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
               allowed_methods=frozenset({"GET", "POST"}), respect_retry_after_header=True)
_session.mount("https://", HTTPAdapter(max_retries=_retry))

# Jamendo 元数据查询：批量 id[] 查询偶发超时/5xx，read=2 让读超时也重试，避免整批名字丢空。
_jam_session = requests.Session()
_jam_retry = Retry(total=3, read=2, connect=2, backoff_factor=0.5,
                   status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset({"GET"}))
_jam_session.mount("https://", HTTPAdapter(max_retries=_jam_retry))


# --- id / 展示 ---
def to_cyanite(track_id: str) -> str:
    return _JAM_TO_CYAN[str(track_id)]


def to_jamendo(cyanite_id: str) -> str:
    # 数据包内的精确映射优先，再退到全库 mapper（非种子曲走这条）
    return _CYAN_TO_JAM.get(cyanite_id) or _CYAN_TO_TRACK[cyanite_id]


def display(cyanite_id: str, track_id: str = "") -> dict:
    if cyanite_id in _DISPLAY:          # 数据包种子曲：有真实 title + artist
        return _DISPLAY[cyanite_id]
    # 其余 catalog 曲：track_id 优先用调用方从 API 响应直接解析出来的（mapper 可能缺新上传曲），
    # 再退到全库 mapper。title/artist Cyanite 库里根本没有（标题就是 {jamendoId}.mp3），留空。
    return {"track_id": track_id or _CYAN_TO_TRACK.get(cyanite_id, ""), "cyanite_id": cyanite_id,
            "title": "", "artist": ""}


def normalize(resp: dict) -> list[dict]:
    """Cyanite {items:[{track,score}]} -> [{cyanite_id, score, track_id}]。
    track_id 直接取自响应里 track.title（Cyanite 上传文件名 = {jamendoId}.mp3），不依赖 mapper。"""
    out = []
    for it in resp.get("items", []):
        track = it.get("track", it)
        out.append({"cyanite_id": track.get("id"), "score": it.get("score"),
                    "track_id": str(track.get("title") or "").removesuffix(".mp3")})
    return out


# --- 检索 ---
def search_by_prompt(query: str, limit: int = config.SEARCH_LIMIT,
                     metadata_filter: dict | None = None) -> list[dict]:
    """freeTextSearch：自然语言 -> 候选曲。metadata_filter 为意图 Agent 生成的硬过滤。"""
    body = {"query": query}
    if metadata_filter:
        body["metadataFilter"] = metadata_filter
    r = _session.post(f"{config.CYANITE_BASE_URL}/private-alpha/library-tracks/search",
                      params={"limit": limit}, json=body, timeout=60)
    r.raise_for_status()
    return normalize(r.json())


def _jamendo_one(track_id: str) -> dict | None:
    """串行查单首 Jamendo，拿到返回 {title, artist}，查不到/失败返回 None。"""
    if not config.JAMENDO_CLIENT_ID or not track_id:
        return None
    try:
        r = _jam_session.get(f"{config.JAMENDO_BASE_URL}/tracks",
                             params={"client_id": config.JAMENDO_CLIENT_ID,
                                     "id": track_id, "format": "json", "limit": 1},
                             timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return None
        return {"title": results[0].get("name", ""), "artist": results[0].get("artist_name", "")}
    except Exception as e:
        print(f"[warn] Jamendo fetch failed for {track_id}: {e}")
        return None


def enrich_meta(cards: list[dict]) -> list[dict]:
    """补 title/artist 并丢弃拿不到名字的卡：CSV 命中保留，缺名的逐首串行查 Jamendo，
    查不到的从结果里剔除（不渲染）。"""
    out = []
    for c in cards:
        if c.get("title"):
            out.append(c); continue
        meta = _jamendo_one(c.get("track_id", ""))
        if meta and meta["title"]:
            c.update(meta)
            out.append(c)
        # 否则丢弃：拿不到真实名字就不渲染
    return out


def search_raw(query: str, limit: int = config.SEARCH_LIMIT) -> list[dict]:
    """freeTextSearch：CSV 命中用本地元数据，未命中批量调 Jamendo API 补 title/artist。"""
    r = _session.post(f"{config.CYANITE_BASE_URL}/private-alpha/library-tracks/search",
                      params={"limit": limit}, json={"query": query}, timeout=60)
    r.raise_for_status()

    rows = []
    for it in r.json().get("items", []):
        track = it["track"]
        cid = track["id"]
        tid = str(track.get("title") or "").removesuffix(".mp3")
        meta = _DISPLAY.get(cid)
        rows.append({"cyanite_id": cid, "track_id": tid, "score": it["score"],
                     "title": meta["title"] if meta else "", "artist": meta["artist"] if meta else ""})

    return enrich_meta(rows)


def find_similar(cyanite_id: str, limit: int = config.SIMILAR_LIMIT) -> list[dict]:
    """#3 similarById（单种子）：一首曲 -> 声学相似曲。"""
    r = _session.post(f"{config.CYANITE_BASE_URL}/private-alpha/library-tracks/{cyanite_id}/similar",
                      params={"limit": limit}, json={}, timeout=60)
    r.raise_for_status()
    return normalize(r.json())


def find_similar_multi(cyanite_ids: list[str], limit: int = config.SIMILAR_LIMIT) -> list[dict]:
    """#4 similar（多种子，≤10）：一组曲 -> 综合声学相似曲。"""
    body = {"tracks": [{"id": cid} for cid in cyanite_ids[:10]]}
    r = _session.post(f"{config.CYANITE_BASE_URL}/private-alpha/library-tracks/similar",
                      params={"limit": limit}, json=body, timeout=60)
    r.raise_for_status()
    return normalize(r.json())


def model_tags(cyanite_id: str, models: list[str]) -> dict:
    """拉某曲的模型标签，给 'Why this track?' 用。"""
    params = [("model", m) for m in models]
    r = _session.get(f"{config.CYANITE_BASE_URL}/library-tracks/{cyanite_id}/models",
                     params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def _selfcheck() -> None:
    """离线自检：种子曲拿到真实 artist；非种子 catalog 曲也能解析出 track_id（只是无 artist）。"""
    pack_cid = next(iter(_DISPLAY))
    d = display(pack_cid)
    assert d["track_id"] and d["artist"], f"种子曲应有 track_id+artist: {d}"
    # 全库里挑一个不在数据包的 catalog 曲
    other_cid = next(c for c in _CYAN_TO_TRACK if c not in _DISPLAY)
    o = display(other_cid)
    assert o["track_id"] and o["artist"] == "", f"非种子曲应有 track_id、artist 为空: {o}"
    assert to_jamendo(other_cid) == o["track_id"]
    # 新上传曲不在 mapper：track_id 应回退到调用方从 API 响应解析的值
    n = display("libtr_doesnotexist", track_id="919998")
    assert n["track_id"] == "919998", f"新曲应用 API 给的 track_id: {n}"
    assert normalize({"items": [{"score": 0.9, "track": {"id": "x", "title": "919998.mp3"}}]}) \
        == [{"cyanite_id": "x", "score": 0.9, "track_id": "919998"}]
    print(f"✅ selfcheck: 种子 {pack_cid}->{d['artist']!r} / 非种子 {other_cid}->track_id {o['track_id']}")


if __name__ == "__main__":
    _selfcheck()
