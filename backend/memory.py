"""接缝 · 记忆系统（队友负责）。

═══════════════════════════════════════════════════════════════════
  跨会话记忆 = 两个 markdown 文件，无 DB（PRD §3）:
    memory/<user_id>.evidence.md   仅追加，原始事实（每行：一首 like 的歌 + 它的「感觉」标签）
    memory/<user_id>.memory.md     自然语言「感觉」画像，证据的派生物
═══════════════════════════════════════════════════════════════════

契约（编排层依赖，签名不变）:
    read_memory(user_id) -> str          画像（memory.md）；/intent 注入、/your-sound 直吐。没有则 ""。
    append_evidence(user_id, prompt, liked_track_ids) -> None
        一轮结束时调用：为每首 like 的歌取「感觉」标签并仅追加，绝不改旧行。
    rewrite_memory(user_id) -> str       从 evidence raw 重建画像，整段重写。

设计取向（用户定）:
- 只用「感觉」维度：mood / character / movement —— 不碰乐器、曲风、BPM 等硬变量。
- 取标签时只请求这三个模型，连乐器的 segment 大块都不下载 → 天然无上下文爆炸。
- 每轮（一个 prompt + 用户选的歌）结束才出画像；永远从 raw 重建，不在旧画像上改 → 防漂移。
"""
from __future__ import annotations
import datetime as _dt
import pathlib
import re
from collections import Counter

MEM_DIR = pathlib.Path(__file__).parent / "memory"
MEM_DIR.mkdir(exist_ok=True)

WINDOW = 30          # 重建只读最近 N 个 like —— evidence.md 可无限增长，喂 LLM 的恒定有界
FEELING_DIMS = ("moods", "character", "movement")
FEELING_MODELS = ["MoodSimpleV2", "CharacterV2", "MovementV2"]   # 只取感觉，不下载硬变量


def _ev_path(user_id: str) -> pathlib.Path:
    return MEM_DIR / f"{user_id}.evidence.md"


def _mem_path(user_id: str) -> pathlib.Path:
    return MEM_DIR / f"{user_id}.memory.md"


def read_evidence(user_id: str) -> str:
    p = _ev_path(user_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def read_memory(user_id: str) -> str:
    p = _mem_path(user_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _feeling_tags(track_id: str) -> list[str]:
    """一首歌的「感觉」标签：mood + character + movement，去重。
    只请求这三个模型——不下载乐器/曲风/BPM（连 segment 大块都不取）。seam: 自检可替换。"""
    from profile import tags as tagmod
    try:
        t = tagmod.for_track(track_id, models=FEELING_MODELS) or {}
    except Exception:
        return []
    out = []
    for d in FEELING_DIMS:
        for tag in t.get(d) or []:
            if tag not in out:
                out.append(tag)
    return out


def append_evidence(user_id: str, whiteboard_context: str, liked_track_ids: list[str]) -> None:
    """一轮结束时把这一轮 like 的每首歌 + 它的感觉标签追加进 evidence.md（仅追加）。"""
    p = _ev_path(user_id)
    if not p.exists():
        p.write_text(f"# evidence · {user_id}\n\n## 反馈记录（每行：一首 like 的歌 + 它的感觉标签）\n",
                     encoding="utf-8")
    ts = _dt.datetime.now().isoformat(timespec="seconds")
    with p.open("a", encoding="utf-8") as f:
        for cid in liked_track_ids:
            feel = ", ".join(_feeling_tags(cid)) or "-"
            f.write(f"- 👍 `{cid}` · 「{whiteboard_context}」 · feel: {feel} · {ts}\n")


_EV_RE = re.compile(r"`([^`]+)`\s*·\s*「(.*?)」\s*·\s*feel:\s*(.*?)\s*·")


def _parse_likes(user_id: str) -> list[dict]:
    """从 evidence.md 解析每首 like 的歌 (id, prompt, [feeling tags])，最旧→最新。"""
    out = []
    for line in read_evidence(user_id).splitlines():
        m = _EV_RE.search(line)
        if not m:
            continue
        feel = [x.strip() for x in m.group(3).split(",") if x.strip() and x.strip() != "-"]
        out.append({"id": m.group(1), "prompt": m.group(2), "feel": feel})
    return out


def _facts(likes: list[dict]) -> dict:
    """把最近 WINDOW 个 like 的感觉标签聚合成 grounding facts（计数）。"""
    recent = likes[-WINDOW:]
    themes: list[str] = []
    cnt: Counter = Counter()
    for ev in recent:
        if ev["prompt"] and ev["prompt"] not in themes:
            themes.append(ev["prompt"])
        cnt.update(ev["feel"])
    top = cnt.most_common(8)
    return {"themes": themes[-5:], "top": [t for t, _ in top],
            "facts": ", ".join(f"{tag} ×{n}" for tag, n in top)}


def _rule_profile(info: dict) -> str:
    """无 LLM key 时的确定性兜底（仍只用真感觉标签）。"""
    feel = "、".join(info["top"][:5])
    return f"你总是被 **{feel}** 这样的感觉吸引。" if feel else "你的感觉画像正在成形。"


def _llm_profile(info: dict) -> str | None:
    """LLM 只措辞、不发明——只喂聚合好的感觉标签 + 用户意图。无 OPENAI key 走兜底。"""
    import config
    if not config.OPENAI_API_KEY:
        return None
    try:
        import intent_agent
        facts = (f"用户搜索时表达的意图: {' / '.join(info['themes']) or '—'}\n"
                 f"他/她 like 的歌曲共有的「感觉」标签（按出现次数）: {info['facts'] or '—'}")
        payload = intent_agent._responses(
            "你在为听者写一段关于「音乐感觉」的画像。只谈情绪、氛围、律动这种感受层面的东西，"
            "绝不提乐器、曲风、BPM 等技术参数。用第二人称写 2-3 句中文，温暖、具体、不浮夸。"
            "只能用给定信息，绝不编造。",
            facts)
        return intent_agent._output_text(payload).strip()
    except Exception:
        return None


def rewrite_memory(user_id: str) -> str:
    """每轮结束后从 evidence raw 重建「感觉」画像。只读最近 WINDOW 个 like（防上下文爆炸），
    永远从 raw 重建（不在旧画像上改）→ 防漂移；只用感觉标签，不碰硬变量。"""
    likes = _parse_likes(user_id)
    if not likes:
        txt = f"# memory · {user_id}\n\n## 你的感觉\n（还没有 like，先选几首喜欢的歌。）\n"
        _mem_path(user_id).write_text(txt, encoding="utf-8")
        return txt

    info = _facts(likes)
    para = _llm_profile(info) or _rule_profile(info)
    themes = "、".join(f"「{t}」" for t in info["themes"]) or "—"
    txt = (f"# memory · {user_id}\n\n## 你的感觉\n{para}\n\n"
           f"---\n_常出现的感觉: {info['facts'] or '—'}_\n"
           f"_最近意图: {themes} · 基于最近 {min(len(likes), WINDOW)}/{len(likes)} 个 like · "
           f"{_dt.datetime.now().isoformat(timespec='seconds')}_\n")
    _mem_path(user_id).write_text(txt, encoding="utf-8")
    return txt


if __name__ == "__main__":
    # self-check: evidence 内联存感觉标签；无 like 不出画像；有 like 基于感觉重建、不含硬变量
    import config as _cfg
    _cfg.OPENAI_API_KEY = ""    # 强制确定性兜底，自检不打网络
    u = "__selftest__"
    for p in (_ev_path(u), _mem_path(u)):
        p.unlink(missing_ok=True)

    fake = {"t1": ["calm", "warm", "flowing"],
            "t2": ["calm", "ethereal", "flowing"],
            "t3": ["chill", "warm"]}
    _feeling_tags = lambda cid: fake.get(cid, [])   # 替换 seam，不打网络

    assert "还没有 like" in rewrite_memory(u), "无 like 不应出画像"

    append_evidence(u, "深夜独处", ["t1", "t2"])      # 一轮
    append_evidence(u, "想要温暖一点", ["t3"])        # 又一轮
    ev = read_evidence(u)
    assert "feel: calm, warm, flowing" in ev, "evidence 应内联存每首的感觉标签"
    assert read_evidence(u).count("\n- ") == 3, "三首 like = 三行，append 不覆盖"

    out = rewrite_memory(u)
    assert "calm" in out and "flowing" in out, "画像应基于感觉标签"
    assert "piano" not in out and "ambient" not in out, "不应出现硬变量（乐器/曲风）"
    for p in (_ev_path(u), _mem_path(u)):
        p.unlink(missing_ok=True)
    print("memory self-check ok")
