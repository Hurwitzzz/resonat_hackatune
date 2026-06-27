"""Cyanite 真连通自检（打真 API，要 .env 里的 CYANITE_API_KEY）。
run: uv run python smoke_cyanite.py
没 key 就跳过；连不通会 raise，连通则打印结果 + OK。
"""
import config
import cyanite

if not config.CYANITE_API_KEY:
    raise SystemExit("跳过：.env 里没填 CYANITE_API_KEY")

hits = cyanite.search_by_prompt("dreamy ambient piano, slow and emotional", limit=3)
assert hits and hits[0]["cyanite_id"], "freeText 应返回带 id 的结果"
print("freeText OK:", hits[0]["cyanite_id"], hits[0]["score"])

sim = cyanite.find_similar(hits[0]["cyanite_id"], limit=3)
assert sim and sim[0]["cyanite_id"], "similarById 应返回结果"
print("similar  OK:", sim[0]["cyanite_id"], sim[0]["score"])

print("✅ cyanite 真连通")
