"""User-defined taste memory, stored as one Markdown file per user (skill format).

Each user's memory lives at  memories/<user_id>.md  — human-readable and
explainable (you can literally open it and read what the system "knows").
A fenced ```json state block at the bottom is the machine-readable source of
truth we parse on load; the body above it is the rendered, human view.

The single entry point is record_feedback(); everything else is read views.

Design choices:
- Preferences are an interpretable per-tag affinity (EMA), never an opaque latent
  — every number traces back to liked tracks + their real Cyanite tags.
- Memory is built from likes (positive). dislike/skip push affinity down (and can
  surface "avoids"); free-text "note" is stored verbatim.
"""
import json
import os
import re
import time

from . import tags as tagmod

MEMORIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memories")
os.makedirs(MEMORIES_DIR, exist_ok=True)

# how strongly each verdict moves affinity
SIGNAL = {"like": 1.0, "play": 0.3, "skip": -0.3, "dislike": -0.8, "note": 0.0}
ALPHA = 0.3          # EMA learning rate for tag affinities
NUM_ALPHA = 0.25     # EMA rate for numeric axes (bpm/valence/arousal)
CAT_DIMS = ["moods", "genres", "instruments", "character", "movement"]
AVOID_THRESHOLD = -0.25


# ---------------------------------------------------------------------------
# storage: parse / render the per-user markdown file
# ---------------------------------------------------------------------------
def _path(user_id):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(user_id))
    return os.path.join(MEMORIES_DIR, f"{safe}.md")


def _empty(user_id):
    return {"user_id": str(user_id), "updated": None,
            "counts": {"like": 0, "dislike": 0, "skip": 0, "play": 0, "note": 0},
            "dims": {d: {} for d in CAT_DIMS},
            "numeric": {k: None for k in ("bpm", "valence", "arousal")},
            "tempo": {}, "vocals": {},
            "scenarios": {},          # mood -> {"bpm": [..], "genres": {..}}
            "notes": [], "evidence": []}


def load(user_id):
    p = _path(user_id)
    if not os.path.exists(p):
        return _empty(user_id)
    text = open(p).read()
    m = re.search(r"```json\s*(\{.*\})\s*```", text, re.S)
    if not m:
        return _empty(user_id)
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return _empty(user_id)


def save(state):
    state["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(_path(state["user_id"]), "w") as f:
        f.write(render_md(state))


# ---------------------------------------------------------------------------
# THE INTERFACE: record one feedback event
# ---------------------------------------------------------------------------
def record_feedback(user_id, track_id, verdict, prompt=None, note=None, track_tags=None):
    """Update a user's markdown taste memory from one feedback event.

    verdict: like | dislike | skip | play | note
    track_tags: optional normalized tags; fetched from Cyanite (cached) if absent.
    Returns the updated memory summary (see summary()).
    """
    state = load(user_id)
    s = SIGNAL.get(verdict, 0.0)
    state["counts"][verdict] = state["counts"].get(verdict, 0) + 1

    if note:
        state["notes"].append({"text": note, "track_id": track_id, "ts": time.time()})

    tags = None
    if verdict != "note":
        tags = track_tags or _safe_tags(track_id)

    if tags and s != 0:
        # categorical affinities (EMA toward the signal)
        for dim in CAT_DIMS:
            for tag in tags.get(dim) or []:
                cell = state["dims"][dim].get(tag, {"aff": 0.0, "n": 0})
                cell["aff"] = round(cell["aff"] + ALPHA * (s - cell["aff"]), 3)
                cell["n"] += 1
                state["dims"][dim][tag] = cell
        if tags.get("tempo"):
            _bump(state["tempo"], tags["tempo"], s)
        # numeric centers + scenario memory only from positive signals
        if s > 0:
            for k in ("bpm", "valence", "arousal"):
                v = tags.get(k)
                if v is not None:
                    cur = state["numeric"][k]
                    state["numeric"][k] = round(v if cur is None else cur + NUM_ALPHA * (v - cur), 2)
            for vc in tags.get("vocals") or []:
                _bump(state["vocals"], vc, 1.0)
            _scenario_update(state, tags)

    # short rolling evidence log (raw layer)
    state["evidence"].append({
        "track_id": track_id, "verdict": verdict, "prompt": prompt,
        "brief": _brief(tags) if tags else None, "ts": time.time()})
    state["evidence"] = state["evidence"][-50:]

    save(state)
    return summary(user_id, _state=state)


def _bump(d, key, s):
    cell = d.get(key, {"aff": 0.0, "n": 0})
    cell["aff"] = round(cell["aff"] + ALPHA * (s - cell["aff"]), 3)
    cell["n"] += 1
    d[key] = cell


def _scenario_update(state, tags):
    mood = (tags.get("moods") or [None])[0]
    if not mood:
        return
    sc = state["scenarios"].setdefault(mood, {"n": 0, "bpm": [], "genres": {}})
    sc["n"] += 1
    if tags.get("bpm"):
        sc["bpm"].append(tags["bpm"])
        sc["bpm"] = sc["bpm"][-30:]
    for g in tags.get("genres") or []:
        sc["genres"][g] = sc["genres"].get(g, 0) + 1


def _safe_tags(track_id):
    try:
        return tagmod.for_track(track_id)
    except Exception:
        return None


def _brief(tags):
    g = (tags.get("genres") or ["?"])[0]
    m = "/".join((tags.get("moods") or [])[:2])
    return f"{g}/{m}" if m else g


# ---------------------------------------------------------------------------
# read views
# ---------------------------------------------------------------------------
def _top_pos(cells, n):
    pos = {t: c["aff"] for t, c in cells.items() if c["aff"] > 0.05}
    total = sum(pos.values()) or 1.0
    return [{"tag": t, "pct": round(100 * a / total), "aff": a}
            for t, a in sorted(pos.items(), key=lambda kv: -kv[1])[:n]]


def _avoids(state):
    out = {}
    for dim, cells in state["dims"].items():
        neg = [t for t, c in cells.items() if c["aff"] < AVOID_THRESHOLD]
        if neg:
            out[dim] = neg
    return out


def summary(user_id, _state=None):
    """Structured memory summary (for GET /your-sound)."""
    st = _state or load(user_id)
    likes = {d: _top_pos(st["dims"][d], 5) for d in CAT_DIMS}
    import statistics
    scen = {}
    for mood, sc in st["scenarios"].items():
        if sc["n"] >= 2 and sc["bpm"]:
            top_g = sorted(sc["genres"], key=sc["genres"].get, reverse=True)[:2]
            scen[mood] = {"n": sc["n"], "median_bpm": round(statistics.median(sc["bpm"])),
                          "genres": top_g}
    return {"user_id": st["user_id"], "counts": st["counts"],
            "likes": likes, "avoids": _avoids(st),
            "numeric": st["numeric"], "vocals": _top_pos(st["vocals"], 2),
            "scenarios": scen, "headline": _headline(st, likes),
            "notes": [n["text"] for n in st["notes"]]}


def _headline(st, likes):
    if not any(likes.values()):
        return "No taste memory yet — like a few tracks first."
    m = ", ".join(x["tag"] for x in likes["moods"][:3])
    g = ", ".join(x["tag"] for x in likes["genres"][:2])
    inst = ", ".join(x["tag"] for x in likes["instruments"][:3])
    bpm = st["numeric"].get("bpm")
    return f"You lean {m} {g}, built on {inst}{f', around {bpm} BPM' if bpm else ''}."


def seed_pool(user_id, prompt=None, limit=None):
    """Liked track ids for similarById seeds (PRD seed pool). prompt filters."""
    st = load(user_id)
    ids = [e["track_id"] for e in reversed(st["evidence"])
           if e["verdict"] == "like" and (prompt is None or e["prompt"] == prompt)]
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i); out.append(i)
    return out[:limit] if limit else out


def prompt_injection(user_id):
    """Compact taste block to prepend to the /intent system prompt."""
    s = summary(user_id)
    if not any(s["likes"].values()):
        return ""
    parts = ["KNOWN LISTENER TASTE (bias interpretation; do not override an explicit new request):",
             "- " + s["headline"]]
    if s["avoids"]:
        av = ", ".join(v for vs in s["avoids"].values() for v in vs)
        parts.append(f"- avoids: {av}")
    for mood, sc in list(s["scenarios"].items())[:3]:
        parts.append(f"- when {mood}: ~{sc['median_bpm']} BPM, {', '.join(sc['genres'])}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# markdown rendering (the human-facing memory artifact)
# ---------------------------------------------------------------------------
def render_md(state):
    s = summary(state["user_id"], _state=state)
    L = []
    L += [f"---",
          f"user_id: {s['user_id']}",
          f"updated: {state.get('updated')}",
          f"likes: {s['counts'].get('like',0)}  dislikes: {s['counts'].get('dislike',0)}  notes: {s['counts'].get('note',0)}",
          f"---", ""]
    L += [f"# 🎧 Taste memory — user {s['user_id']}", "",
          f"**Your sound:** {s['headline']}", ""]

    L.append("## You like")
    for dim in CAT_DIMS:
        items = s["likes"][dim]
        if items:
            L.append(f"- **{dim}**: " + " · ".join(f"{x['tag']} ({x['pct']}%)" for x in items))
    num = s["numeric"]
    L.append(f"- **tempo/energy**: "
             f"{('~'+str(num['bpm'])+' BPM') if num.get('bpm') else 'n/a'}"
             f"{', valence '+str(num['valence']) if num.get('valence') is not None else ''}"
             f"{', arousal '+str(num['arousal']) if num.get('arousal') is not None else ''}")
    if s["vocals"]:
        L.append("- **vocals**: " + ", ".join(x["tag"] for x in s["vocals"]))
    L.append("")

    if s["avoids"]:
        L.append("## You avoid")
        for dim, vs in s["avoids"].items():
            L.append(f"- **{dim}**: " + ", ".join(vs))
        L.append("")

    if s["scenarios"]:
        L.append("## Scenario memory")
        for mood, sc in s["scenarios"].items():
            L.append(f"- **{mood}** → ~{sc['median_bpm']} BPM, {', '.join(sc['genres'])} (from {sc['n']} likes)")
        L.append("")

    if s["notes"]:
        L.append("## Notes from you")
        for n in s["notes"][-8:]:
            L.append(f"- “{n}”")
        L.append("")

    if state["evidence"]:
        L.append("## Recent feedback")
        emoji = {"like": "👍", "dislike": "👎", "skip": "⏭", "play": "▶", "note": "📝"}
        for e in state["evidence"][-8:][::-1]:
            tag = f" — {e['brief']}" if e.get("brief") else ""
            pr = f"  _(prompt: {e['prompt']})_" if e.get("prompt") else ""
            L.append(f"- {emoji.get(e['verdict'],'?')} `{e['track_id']}`{tag}{pr}")
        L.append("")

    L += ["<!-- machine state — do not edit -->", "```json",
          json.dumps(state, ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(L)
