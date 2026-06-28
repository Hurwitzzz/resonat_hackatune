"""Normalize raw Cyanite model outputs into a flat TrackTags dict."""
from . import cyanite_tags


def _iter(outputs):
    if isinstance(outputs, dict) and isinstance(outputs.get("items"), list):
        yield from outputs["items"]
    elif isinstance(outputs, list):
        yield from outputs


def _flat_tags(mo, thresh=0.2, topk=6):
    """扁平 tag 列表，兼容两种 Cyanite 形态：汇总 `tags`，或分段 `segments`。
    segments 形态在时间轴上对每个 key 取 max → 过阈值 → top-K，把几百个浮点
    压成几个字符串——这是防上下文爆炸的根因处理（在摄入处缩减，不在喂处）。"""
    if isinstance(mo.get("tags"), list):
        return mo["tags"]
    vals = (mo.get("segments") or {}).get("values") or {}
    if not vals:
        return []
    scored = sorted(((k, max(v or [0.0])) for k, v in vals.items()), key=lambda kv: -kv[1])
    return [k for k, m in scored if m >= thresh][:topk]


def normalize(outputs) -> dict:
    t = {"moods": [], "genres": [], "instruments": [], "character": [],
         "movement": [], "bpm": None, "tempo": None, "valence": None,
         "arousal": None, "energy": None, "emotion": None, "era": None,
         "vocals": [], "description": None,
         # richer fields (present only when the extra models are requested)
         "moodAdvanced": [], "musicFor": [], "freeGenres": [], "subgenres": [],
         "key": None}
    for mo in _iter(outputs):
        v = mo.get("version")
        if v == "MoodSimpleV2":
            t["moods"] = _flat_tags(mo, topk=4)
        elif v == "MainGenreV2":
            t["genres"] = _flat_tags(mo, topk=3)
        elif v == "InstrumentsV2":
            t["instruments"] = _flat_tags(mo, topk=6)
        elif v == "CharacterV2":
            t["character"] = _flat_tags(mo, topk=4)
        elif v == "MovementV2":
            t["movement"] = _flat_tags(mo, topk=3)
        elif v == "BpmV2":
            t["bpm"] = mo.get("tag")
        elif v == "TempoV1":
            t["tempo"] = mo.get("tag")
        elif v == "ValenceArousalV2":
            sc = mo.get("scores") or {}
            t["valence"], t["arousal"] = sc.get("valence"), sc.get("arousal")
            t["energy"] = mo.get("energyLevel")
            t["emotion"] = mo.get("emotionProfile")
        elif v == "MusicalEraV2":
            t["era"] = mo.get("tag")
        elif v == "VocalsV2":
            t["vocals"] = mo.get("tags") or []
        elif v == "AutoDescriptionV2":
            t["description"] = mo.get("description")
        elif v == "MoodAdvancedV2":
            t["moodAdvanced"] = mo.get("tags") or []
        elif v == "MusicForV1":
            t["musicFor"] = mo.get("tags") or []
        elif v == "FreeGenreV3":
            t["freeGenres"] = mo.get("tags") or []
        elif v == "SubgenreV2":
            t["subgenres"] = mo.get("tags") or []
        elif v == "KeyV2":
            t["key"] = mo.get("tag")
    return t


def for_track(track_id, models=None) -> dict:
    """Cached, normalized tags for one Cyanite track id (libtr_...)."""
    return normalize(cyanite_tags.get_model_outputs(track_id, models))
