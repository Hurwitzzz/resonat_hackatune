"""重复度自检 · 真打 Cyanite API，量化"自然语言召回"与"相似度召回"的重叠。

写法对齐 notebooks/cyanite_model_outputs.ipynb：自带 session（x-api-key 头）、
检索函数返回原始 {items, pageInfo}、用 track['title'] 展示、show_results 打分。
不 import 项目的 cyanite.py，保持和 notebook 一样自包含、可单独跑。

担心的点：confirm() 跑 freeText 给一批曲，like 后 _backfill 用这些曲做种子跑
similar，如果两批高度重叠，similar 回填就只是把 freeText 已展示的曲再端一遍。

run: 在 .env 填好 CYANITE_API_KEY 后，  uv run python demo_overlap.py
"""
import os

import requests
from dotenv import load_dotenv

# --- 和 notebook cell-1 一致：load_dotenv + session(x-api-key) ---
load_dotenv()  # 从 .env 读 CYANITE_API_KEY
API_KEY = os.environ.get("CYANITE_API_KEY", "")
BASE_URL = "https://rest-api.cyanite.ai/v1"

session = requests.Session()
session.headers.update({"x-api-key": API_KEY})


# --- 三个检索函数：照搬 notebook 的签名/返回（原始 {items, pageInfo}），带 metadata_filter ---
def search_by_prompt(query, limit=20, metadata_filter=None):
    # POST /private-alpha/library-tracks/search -> {items: [{track, score}], pageInfo}
    body = {"query": query}
    if metadata_filter:
        body["metadataFilter"] = metadata_filter
    resp = session.post(
        f"{BASE_URL}/private-alpha/library-tracks/search",
        params={"limit": limit}, json=body, timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def find_similar(track_id, limit=20, metadata_filter=None):
    # POST /private-alpha/library-tracks/{id}/similar -> {items: [{track, score}], pageInfo}
    body = {}
    if metadata_filter:
        body["metadataFilter"] = metadata_filter
    resp = session.post(
        f"{BASE_URL}/private-alpha/library-tracks/{track_id}/similar",
        params={"limit": limit}, json=body, timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def find_similar_multi(track_ids, limit=20, metadata_filter=None):
    # POST /private-alpha/library-tracks/similar -> {items: [{track, score}], pageInfo}
    body = {"tracks": [{"id": tid} for tid in track_ids]}
    if metadata_filter:
        body["metadataFilter"] = metadata_filter
    resp = session.post(
        f"{BASE_URL}/private-alpha/library-tracks/similar",
        params={"limit": limit}, json=body, timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# --- 重复度逻辑搭在上面 ---
PROMPTS = [
    "dreamy ambient piano, slow and emotional",
    "high energy electronic dance, festival mainstage",
    "melancholic acoustic guitar, rainy afternoon",
    "aggressive trap beat with heavy 808s",
    "warm lo-fi hip hop to study to",
]
LIKE_TOP = 2          # 模拟 like freeText 前几首作种子
VISIBLE_N = 5         # 右下推荐一次展示几首（和编排 VISIBLE_N 对齐）
SEARCH_LIMIT = 20
SIMILAR_LIMIT = 20


def ids(res):
    # notebook 风格：从 {items:[{track, score}]} 里取 track.id
    return [it.get("track", it).get("id") for it in res.get("items", [])]


def show_results(res, list_n=5):
    # 照搬 notebook show_results：打 score | id | title
    for it in res.get("items", [])[:list_n]:
        track = it.get("track", it)
        score = it.get("score")
        score_str = f"{score:.3f}  " if isinstance(score, (int, float)) else ""
        print(f"    {score_str}{track.get('id')}  |  {track.get('title')}")


def run_one(prompt):
    free = search_by_prompt(prompt, limit=SEARCH_LIMIT)
    free_ids = ids(free)
    seeds = free_ids[:LIKE_TOP]

    # 和 orchestrator._expand_pool 一致：>=2 种子用 multi，1 个用单种子
    if len(seeds) >= 2:
        sim = find_similar_multi(seeds, limit=SIMILAR_LIMIT)
    elif seeds:
        sim = find_similar(seeds[0], limit=SIMILAR_LIMIT)
    else:
        sim = {"items": []}
    sim_ids = ids(sim)

    free_set, sim_set = set(free_ids), set(sim_ids)
    inter = free_set & sim_set
    union = free_set | sim_set
    sim_minus_seeds = [c for c in sim_ids if c not in seeds]  # 种子本身必然相似，扣掉
    return {
        "prompt": prompt, "free": free, "sim": sim,
        "n_free": len(free_ids), "n_sim": len(sim_ids),
        "overlap": len(inter),
        "overlap_pct": (len(inter) / len(sim_set) * 100) if sim_set else 0.0,
        "jaccard": (len(inter) / len(union) * 100) if union else 0.0,
        "novel_after_seeds": sum(c not in free_set for c in sim_minus_seeds),
        "n_minus_seeds": len(sim_minus_seeds),
        "overlap_visible5": len(set(free_ids[:VISIBLE_N]) & sim_set),
    }


def main():
    if not API_KEY:
        raise SystemExit("跳过：.env 里没填 CYANITE_API_KEY")

    rows = []
    for p in PROMPTS:
        r = run_one(p)
        rows.append(r)
        print(f"\n■ {p}")
        print(f"  freeText 召回 {r['n_free']}：")
        show_results(r["free"], list_n=3)
        print(f"  similar 召回 {r['n_sim']}（种子={LIKE_TOP}）：")
        show_results(r["sim"], list_n=3)
        print(f"  → similar∩freeText = {r['overlap']} 首，重叠率 {r['overlap_pct']:.0f}%"
              f"（Jaccard {r['jaccard']:.0f}%）")
        print(f"  → 扣掉种子后 similar 新曲 {r['novel_after_seeds']}/{r['n_minus_seeds']}；"
              f"落在可见前{VISIBLE_N} {r['overlap_visible5']} 首")

    n = len(rows)
    avg = lambda k: sum(r[k] for r in rows) / n
    print("\n" + "=" * 56)
    print(f"平均重叠率(similar 中来自 freeText)：{avg('overlap_pct'):.0f}%")
    print(f"平均 Jaccard：                      {avg('jaccard'):.0f}%")
    print(f"平均落在可见前{VISIBLE_N}的 similar：    {avg('overlap_visible5'):.1f} 首")
    hi = avg("overlap_pct")
    verdict = "高度冗余，similar 回填几乎只在重端 freeText" if hi >= 50 else \
              "中等冗余，similar 仍带来可观新曲" if hi >= 20 else \
              "冗余低，两条召回路互补"
    print(f"判读：{verdict}")


if __name__ == "__main__":
    main()
