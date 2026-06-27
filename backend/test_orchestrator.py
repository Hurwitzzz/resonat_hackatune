"""编排框架自检。monkeypatch 三个接缝（cyanite / intent_compiler / memory），离线跑主循环。
新逻辑：like 只记 liked 种子（不搜索）；similarById 只由 dislike 触发，种子是 liked 曲。
run: uv run pytest -v
"""
from fastapi.testclient import TestClient

import app
import orchestrator as orch

client = TestClient(app.app)

SEARCH = [{"cyanite_id": f"libtr_{i}", "score": 1.0 - i / 10} for i in range(8)]   # 8 首
SIMILAR = [{"cyanite_id": f"sim_{i}", "score": 0.9 - i / 10} for i in range(3)]    # 单种子相似
MULTI = [{"cyanite_id": f"multi_{i}", "score": 0.95 - i / 10} for i in range(3)]   # 多种子相似


def _fake_seams(monkeypatch, tmp_path):
    """返回计数器 dict，记录单种子 / 多种子相似各被调了几次。"""
    calls = {"similar": 0, "multi": 0}

    def fake_similar(cid, limit=20):
        calls["similar"] += 1
        return SIMILAR

    def fake_multi(cids, limit=20):
        calls["multi"] += 1
        return MULTI

    monkeypatch.setattr(orch.cyanite, "search_by_prompt", lambda q, limit=20: SEARCH)
    monkeypatch.setattr(orch.cyanite, "find_similar", fake_similar)
    monkeypatch.setattr(orch.cyanite, "find_similar_multi", fake_multi)
    monkeypatch.setattr(orch.cyanite, "display",
                        lambda cid: {"track_id": cid, "cyanite_id": cid, "title": "T", "artist": "A"})
    monkeypatch.setattr(orch.intent_compiler, "compile_query_card",
                        lambda posts, profile_md="": {
                            "interpretation_plain": "test intent",
                            "free_text_query": "test intent",
                            "soft_targets": [],
                            "negatives": [],
                        })
    monkeypatch.setattr(orch.memory, "_ev_path", lambda u: tmp_path / f"{u}.evidence.md")
    monkeypatch.setattr(orch.memory, "_mem_path", lambda u: tmp_path / f"{u}.memory.md")
    monkeypatch.setattr(orch.user_profiles, "liked_cyanite_ids", lambda u: [])
    return calls


def _confirmed(user_id, monkeypatch, tmp_path):
    calls = _fake_seams(monkeypatch, tmp_path)
    sid = client.post("/intent", json={"text": "dark", "user_id": user_id}).json()["session_id"]
    client.post("/intent/confirm", json={"session_id": sid})
    return sid, calls


def test_intent_does_not_search_until_confirm(monkeypatch, tmp_path):
    hit = {"n": 0}
    _fake_seams(monkeypatch, tmp_path)
    monkeypatch.setattr(orch.cyanite, "search_by_prompt",
                        lambda q, limit=20: hit.update(n=hit["n"] + 1) or SEARCH)
    sid = client.post("/intent", json={"text": "dark betrayal", "user_id": "u1"}).json()["session_id"]
    client.post("/intent/follow-up", json={"session_id": sid, "text": "more restrained"})
    assert hit["n"] == 0  # 确认门：确认前不检索


def test_confirm_fills_visible_and_backlog(monkeypatch, tmp_path):
    sid, _ = _confirmed("u1", monkeypatch, tmp_path)
    body = client.post("/intent/confirm", json={"session_id": sid}).json()
    assert len(body["cards"]) == orch.config.VISIBLE_N
    assert len(orch.SESSIONS[sid]["free_text_backlog"]) == len(SEARCH) - orch.config.VISIBLE_N


def test_like_records_seed_without_searching(monkeypatch, tmp_path):
    sid, calls = _confirmed("u2", monkeypatch, tmp_path)
    before = [c["track_id"] for c in orch.SESSIONS[sid]["visible_cards"]]
    body = client.post("/feedback", json={"session_id": sid, "track_id": "libtr_0", "verdict": "like"}).json()
    assert calls["similar"] == 0                       # like 不触发搜索
    assert body["candidate_pool_size"] == 0            # 候选池仍空
    assert orch.SESSIONS[sid]["liked_tracks"] == ["libtr_0"]
    assert [c["track_id"] for c in body["cards"]] == before  # 当前列表不变
    assert (tmp_path / "u2.evidence.md").read_text(encoding="utf-8").count("\n- ") == 1


def test_dislike_with_one_like_uses_single_seed(monkeypatch, tmp_path):
    sid, calls = _confirmed("u3", monkeypatch, tmp_path)
    client.post("/feedback", json={"session_id": sid, "track_id": "libtr_0", "verdict": "like"})
    assert calls["similar"] == 0 and calls["multi"] == 0   # like 后仍未搜索
    body = client.post("/feedback", json={"session_id": sid, "track_id": "libtr_1", "verdict": "dislike"}).json()
    assert calls["similar"] == 1 and calls["multi"] == 0   # 1 个 liked → 单种子
    ids = [c["track_id"] for c in body["cards"]]
    assert "libtr_1" not in ids                            # 被移除
    assert "sim_0" in ids                                  # 最高 similar_score 回填
    refill = next(c for c in body["cards"] if c["track_id"] == "sim_0")
    assert "final_score" not in refill and "ranking_basis" not in refill  # debug metadata 不给前端
    assert len(ids) == orch.config.VISIBLE_N               # 槽位数不变


def test_dislike_with_two_likes_uses_multi_seed(monkeypatch, tmp_path):
    sid, calls = _confirmed("u6", monkeypatch, tmp_path)
    client.post("/feedback", json={"session_id": sid, "track_id": "libtr_0", "verdict": "like"})
    client.post("/feedback", json={"session_id": sid, "track_id": "libtr_2", "verdict": "like"})
    body = client.post("/feedback", json={"session_id": sid, "track_id": "libtr_1", "verdict": "dislike"}).json()
    assert calls["multi"] == 1 and calls["similar"] == 0   # 2 个 liked → 多种子 multi
    ids = [c["track_id"] for c in body["cards"]]
    assert "multi_0" in ids                                # multi 结果回填
    assert len(ids) == orch.config.VISIBLE_N


def test_dislike_without_any_like_uses_backlog(monkeypatch, tmp_path):
    sid, calls = _confirmed("u4", monkeypatch, tmp_path)
    body = client.post("/feedback", json={"session_id": sid, "track_id": "libtr_0", "verdict": "dislike"}).json()
    assert calls["similar"] == 0                         # 没 liked 种子 → 不搜索
    ids = [c["track_id"] for c in body["cards"]]
    assert "libtr_0" not in ids                          # 被移除
    assert "libtr_5" in ids                              # 用 freeText backlog 补位
    assert len(ids) == orch.config.VISIBLE_N


def test_pool_reused_when_liked_set_unchanged(monkeypatch, tmp_path):
    sid, calls = _confirmed("u5", monkeypatch, tmp_path)
    client.post("/feedback", json={"session_id": sid, "track_id": "libtr_0", "verdict": "like"})
    client.post("/feedback", json={"session_id": sid, "track_id": "libtr_1", "verdict": "dislike"})
    client.post("/feedback", json={"session_id": sid, "track_id": "libtr_2", "verdict": "dislike"})
    assert calls["similar"] == 1  # liked 集合没变 → 候选池复用，不重复搜


def test_explain_uses_historical_similar_intersection(monkeypatch, tmp_path):
    sid, calls = _confirmed("u7", monkeypatch, tmp_path)
    (tmp_path / "u7.evidence.md").write_text(
        "# evidence · u7\n\n## 反馈记录\n- 「old focus」→ liked hist_1   (2026-06-27T20:00:00)\n",
        encoding="utf-8",
    )
    (tmp_path / "u7.memory.md").write_text(
        "# memory · u7\n\nThe listener likes quiet, restrained focus tracks.\n",
        encoding="utf-8",
    )

    def fake_similar(cid, limit=20):
        calls["similar"] += 1
        assert cid == "libtr_0"
        return [{"cyanite_id": "hist_1", "score": 0.91}]

    captured = {}

    def fake_build_explanation(profile_md, query_card, liked_track_tags, recommended_track_tags,
                               recommendation_meta, explanation_example=None, recommended_track=None):
        captured.update({
            "profile_md": profile_md,
            "query_card": query_card,
            "liked_track_tags": liked_track_tags,
            "recommended_track_tags": recommended_track_tags,
            "recommendation_meta": recommendation_meta,
            "explanation_example": explanation_example,
            "recommended_track": recommended_track,
        })
        return {"why_text": "Because it connects to a previous liked track.", "evidence": []}

    monkeypatch.setattr(orch.cyanite, "find_similar", fake_similar)
    monkeypatch.setattr(orch.cyanite, "model_tags", lambda cid, models: {"track": cid, "models": models})
    monkeypatch.setattr(orch.explanation_builder, "build_explanation", fake_build_explanation)

    body = client.post("/explain", json={"session_id": sid, "track_id": "libtr_0"}).json()

    assert body["why_text"].startswith("Because")
    assert calls["similar"] == 1
    assert captured["profile_md"].startswith("# memory")
    assert captured["query_card"]["free_text_query"] == "test intent"
    assert captured["recommended_track_tags"]["track"] == "libtr_0"
    assert captured["liked_track_tags"]["track"] == "hist_1"
    assert captured["recommended_track"]["cyanite_id"] == "libtr_0"
    assert captured["explanation_example"] == {
        "track_id": "hist_1",
        "example_type": "historical_like",
        "similar_score": 0.91,
        "selection_basis": "historical_similarity",
        "title": "T",
        "artist": "A",
    }


def test_explain_uses_provided_user_likes_when_evidence_is_empty(monkeypatch, tmp_path):
    sid, calls = _confirmed("provided_user", monkeypatch, tmp_path)

    def fake_similar(cid, limit=20):
        calls["similar"] += 1
        return [{"cyanite_id": "provided_hist", "score": 0.93}]

    captured = {}

    def fake_build_explanation(profile_md, query_card, liked_track_tags, recommended_track_tags,
                               recommendation_meta, explanation_example=None, recommended_track=None):
        captured["explanation_example"] = explanation_example
        captured["liked_track_tags"] = liked_track_tags
        return {"why_text": "Because it connects to provided history.", "evidence": []}

    monkeypatch.setattr(orch.user_profiles, "liked_cyanite_ids", lambda u: ["provided_hist"])
    monkeypatch.setattr(orch.cyanite, "find_similar", fake_similar)
    monkeypatch.setattr(orch.cyanite, "model_tags", lambda cid, models: {"track": cid})
    monkeypatch.setattr(orch.explanation_builder, "build_explanation", fake_build_explanation)

    body = client.post("/explain", json={"session_id": sid, "track_id": "libtr_0"}).json()

    assert body["why_text"].startswith("Because")
    assert captured["liked_track_tags"]["track"] == "provided_hist"
    assert captured["explanation_example"]["track_id"] == "provided_hist"
    assert captured["explanation_example"]["similar_score"] == 0.93


def test_unknown_session_404(monkeypatch, tmp_path):
    _fake_seams(monkeypatch, tmp_path)
    assert client.post("/intent/confirm", json={"session_id": "nope"}).status_code == 404
