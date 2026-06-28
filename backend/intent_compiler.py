"""接缝 · 意图编译（队友负责：LLM + prompt）。

═══════════════════════════════════════════════════════════════════
  这个文件归同伴。编排层只依赖下面这一个函数签名，别的随你换。
  你要做的：把白板便签 + 用户记忆画像，编译成一张 Query Card。
═══════════════════════════════════════════════════════════════════

契约（编排层依赖，不要改签名）:
    compile_query_card(posts, profile_md) -> dict

  入参:
    posts:      白板便签列表，按时间顺序。每项 {"role","text", ...}
                role ∈ {"initial_prompt", "follow_up"}
    profile_md: 该用户 memory.md 的自然语言画像（可能为空字符串）。
                PRD ⑧：把它注进系统 prompt，让 Query Card 自带"你的声音"。

  返回 Query Card dict（字段名固定，前端/编排都按它来）:
    {
      "interpretation_plain": str,        # 一句大白话"我把你的需求理解成…"
      "free_text_query":      str,        # 打进 freeTextSearch 的英文查询
      "soft_targets": [{"dim","value","weight"}],  # 软目标，无则 []
      "negatives":    [{"dim","value"}],           # 负向，只扣分不剔除，无则 []
    }

实现说明：有 OPENAI_API_KEY 时用 LLM 编译 Query Card；没有 key 时走
deterministic fallback，让离线编排和测试仍可运行。签名保持不变。
"""
from __future__ import annotations

import json
import re

import requests

import config


CYANITE_VOCABULARY_GUIDE = """Cyanite vocabulary guide:
- MoodSimpleV2: calm, chill, dark, energetic, epic, happy, romantic, sad, scary, sexy, ethereal, uplifting.
- MoodAdvancedV2 examples: peaceful, quiet, reflective, relaxed, soothing, tranquil, warm, hopeful, intimate, dreamy, cinematic, melancholic, inspirational, thoughtful, delicate.
- CharacterV2: warm, sparse, sophisticated, ethereal, mysterious, playful, powerful, retro, unpolished, cool.
- MainGenreV2: ambient, classical, electronic, folkCountry, jazz, pop, rock, singerSongwriter, sound, soundtrack.
- InstrumentsV2 examples: piano, acousticGuitar, electricGuitar, synth, strings, percussion, drumKit, electronicDrums, bass, cello, violin, woodwinds.
- MovementV2: steady, flowing, pulsing, nonrhythmic, groovy, driving.
- TempoV1: slow, mediumSlow, medium, mediumFast, fast.
- Energy/valence-arousal: low, medium, high, positive, neutral, negative.
- VocalsV2: instrumental, male, female; vocal presence: low, medium, high.
- MusicForV1 examples: focus, work, study, background, night, nightDrive, cinematic, film, relaxation, reading, meditation, walk, city, drama.
"""

QUERY_CARD_EXAMPLES = """Examples:

Example A - initial note plus taste profile
Whiteboard posts:
1. initial_prompt: Find me something calm and cinematic for working late at night. I want soft piano or warm acoustic guitar, low energy, gentle rhythm, mostly instrumental, and a slightly hopeful mood.
Taste profile:
You often like warm acoustic textures, reflective background music, and low-energy instrumental tracks.
Return:
{
  "interpretation_plain": "Because this is for late-night work, I will keep the search in focus/background territory: calm, quiet, low energy, and low vocal presence. Since you often lean toward warm acoustic textures, piano and acousticGuitar should lead without becoming distracting.",
  "free_text_query": "calm quiet focus background night low energy low vocal presence instrumental piano acousticGuitar warm reflective hopeful steady",
  "soft_targets": [
    {"dim": "musicFor", "value": "focus", "weight": 0.9},
    {"dim": "musicFor", "value": "background", "weight": 0.85},
    {"dim": "mood", "value": "calm", "weight": 0.85},
    {"dim": "energy", "value": "low", "weight": 0.8},
    {"dim": "vocals", "value": "instrumental", "weight": 0.75}
  ],
  "negatives": [{"dim": "vocals", "value": "high vocal presence"}]
}

Example B - follow-up steering
Whiteboard posts:
1. initial_prompt: I want something calm and dreamy for reading.
2. follow_up: Make it a little more energetic, but still not distracting.
Taste profile:
You often like ethereal ambient music, soft synths, and instrumental background tracks.
Return:
{
  "interpretation_plain": "The follow-up shifts the target from purely calm reading music toward gentle momentum. I will keep it background-friendly and instrumental, but raise movement and energy slightly with ethereal synth textures.",
  "free_text_query": "background reading calm dreamy ethereal instrumental synth mediumSlow medium energy gentle movement low vocal presence",
  "soft_targets": [
    {"dim": "musicFor", "value": "reading", "weight": 0.85},
    {"dim": "mood", "value": "dreamy", "weight": 0.8},
    {"dim": "movement", "value": "flowing", "weight": 0.7},
    {"dim": "energy", "value": "medium", "weight": 0.6},
    {"dim": "instrument", "value": "synth", "weight": 0.65}
  ],
  "negatives": [{"dim": "vocals", "value": "high vocal presence"}]
}
"""


SYSTEM_PROMPT = f"""You compile a listener's whiteboard notes into a Cyanite free-text search query.

Return only the requested JSON shape. Do not recommend tracks.

Rules:
- Respect every whiteboard post, including follow-up steering. Later posts refine the current intent.
- Use the taste profile as preference context, not as a replacement for the current request.
- Optimize free_text_query for Cyanite audio search using terms close to Cyanite tags: mood, genre, character, instrumentation, energy, tempo, movement, vocal presence, era, and use case.
- interpretation_plain is the first explainability moment. It must not simply paraphrase the user. Explain how you translated the request into searchable audio traits and, when available, how the taste profile nudges the target.
- Keep interpretation_plain concise: 2 short sentences, 35-60 words total. Use user-facing natural English, but anchor important words in Cyanite-style tags.
- Avoid copying long phrases from the user's prompt. Prefer inferred traits, e.g. "late-night work" -> focus/background, quiet, low energy, low vocal presence, steady or nonrhythmic movement.
- soft_targets are helpful audio attributes with weights from 0.0 to 1.0.
- negatives are things to down-rank, not hard filters.

{CYANITE_VOCABULARY_GUIDE}

{QUERY_CARD_EXAMPLES}
"""

QUERY_CARD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["interpretation_plain", "free_text_query", "soft_targets", "negatives"],
    "properties": {
        "interpretation_plain": {"type": "string"},
        "free_text_query": {"type": "string"},
        "soft_targets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["dim", "value", "weight"],
                "properties": {
                    "dim": {"type": "string"},
                    "value": {"type": "string"},
                    "weight": {"type": "number"},
                },
            },
        },
        "negatives": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["dim", "value"],
                "properties": {
                    "dim": {"type": "string"},
                    "value": {"type": "string"},
                },
            },
        },
    },
}


def compile_query_card(posts: list[dict], profile_md: str = "") -> dict:
    """Compile whiteboard posts + taste profile into the backend Query Card contract."""
    if not config.OPENAI_API_KEY:
        return _fallback_query_card(posts, profile_md)
    return _query_card_from_openai(posts, profile_md)


def _query_card_from_openai(posts: list[dict], profile_md: str) -> dict:
    response = requests.post(
        f"{config.OPENAI_BASE_URL.rstrip('/')}/responses",
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.OPENAI_MODEL,
            "instructions": SYSTEM_PROMPT,
            "input": [{
                "role": "user",
                "content": [{"type": "input_text", "text": _build_user_prompt(posts, profile_md)}],
            }],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "cyanite_query_card",
                    "strict": True,
                    "schema": QUERY_CARD_SCHEMA,
                }
            },
        },
        timeout=config.OPENAI_TIMEOUT,
    )
    response.raise_for_status()
    card = _normalize_query_card(json.loads(_extract_output_text(response.json())))
    return _finalize_query_card(card, posts, profile_md)


def _build_user_prompt(posts: list[dict], profile_md: str) -> str:
    lines = ["Whiteboard posts, chronological:"]
    for i, post in enumerate(_clean_posts(posts), 1):
        lines.append(f"{i}. {post['role']}: {post['text']}")
    lines.append("")
    lines.append("User taste profile:")
    lines.append(profile_md.strip() or "(none yet)")
    lines.append("")
    lines.append("Output guidance:")
    lines.append("- interpretation_plain: explain the inference from request/profile to Cyanite-style sound traits; do not restate the prompt.")
    lines.append("- free_text_query: compact English search phrase using Cyanite-style vocabulary from the guide.")
    return "\n".join(lines)


def _fallback_query_card(posts: list[dict], profile_md: str) -> dict:
    texts = [p["text"] for p in _clean_posts(posts)]
    profile = profile_md.strip()
    request_text = "; ".join(texts)
    traits = _infer_cyanite_traits(request_text, profile)
    query_parts = traits[:]
    if profile:
        query_parts.append(_short_profile_hint(profile))
    query = ", ".join(dict.fromkeys(part for part in query_parts if part))
    return {
        "interpretation_plain": _fallback_interpretation(request_text, profile, traits),
        "free_text_query": query,
        "soft_targets": _fallback_soft_targets(traits),
        "negatives": _fallback_negatives(query),
    }


def _finalize_query_card(card: dict, posts: list[dict], profile_md: str) -> dict:
    """Keep the search query from the LLM, but force the UI explanation to be analytical."""
    request_text = "; ".join(p["text"] for p in _clean_posts(posts))
    if _looks_like_prompt_paraphrase(card.get("interpretation_plain", ""), request_text):
        traits = _traits_from_card_or_text(card, request_text, profile_md)
        card["interpretation_plain"] = _fallback_interpretation(request_text, profile_md, traits)
    return card


def _looks_like_prompt_paraphrase(interpretation: str, request_text: str) -> bool:
    text = interpretation.strip()
    if len(text.split()) < 18:
        return True
    request_words = _content_words(request_text)
    if not request_words:
        return False
    interpretation_words = set(_content_words(text))
    overlap = sum(1 for word in request_words if word in interpretation_words) / len(request_words)
    analysis_markers = {
        "because", "translating", "translated", "so", "therefore", "means",
        "suggests", "prioritize", "down-rank", "distraction", "profile", "nudges",
    }
    has_analysis = any(marker in text.lower() for marker in analysis_markers)
    return overlap >= 0.45 and not has_analysis


def _content_words(text: str) -> list[str]:
    stop = {
        "the", "and", "or", "a", "an", "to", "for", "with", "me", "i", "want",
        "something", "find", "mostly", "slightly", "this", "that", "your", "my",
        "into", "music", "sound", "track", "tracks",
    }
    return [
        word
        for word in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower())
        if word not in stop
    ]


def _traits_from_card_or_text(card: dict, request_text: str, profile_md: str) -> list[str]:
    traits = [
        str(target.get("value", "")).strip()
        for target in card.get("soft_targets", [])
        if isinstance(target, dict) and str(target.get("value", "")).strip()
    ]
    traits.extend(_infer_cyanite_traits(f"{request_text}; {card.get('free_text_query', '')}", profile_md))
    return list(dict.fromkeys(traits))


def _clean_posts(posts: list[dict]) -> list[dict]:
    clean = []
    for post in posts:
        text = str(post.get("text", "")).strip()
        if text:
            clean.append({"role": str(post.get("role", "post")), "text": text})
    return clean


def _fallback_negatives(query: str) -> list[dict]:
    negatives = []
    if re.search(r"\b(less|no|minimal|without)\s+vocals?\b|\binstrumental\b", query, re.I):
        negatives.append({"dim": "vocals", "value": "vocal"})
    return negatives


def _infer_cyanite_traits(request_text: str, profile_md: str) -> list[str]:
    text = f"{request_text} {profile_md}".lower()
    traits: list[str] = []
    if re.search(r"\b(calm|quiet|peaceful|relax|relaxed|soft|gentle)\b", text):
        traits.extend(["calm", "peaceful", "quiet", "low energy"])
    if re.search(r"\b(late[- ]?night|night|midnight|sleep)\b", text):
        traits.extend(["night", "intimate", "warm"])
    if re.search(r"\b(work|working|focus|study|reading|background)\b", text):
        traits.extend(["focus", "background", "low vocal presence", "steady movement"])
    if re.search(r"\b(cinematic|film|scene|soundtrack)\b", text):
        traits.extend(["cinematic", "soundtrack", "reflective"])
    if re.search(r"\b(hopeful|uplifting|positive|warm)\b", text):
        traits.extend(["hopeful", "warm", "positive"])
    if re.search(r"\b(sad|melancholic|melancholy|lonely)\b", text):
        traits.extend(["melancholic", "reflective"])
    if re.search(r"\b(piano)\b", text):
        traits.append("piano")
    if re.search(r"\b(acoustic guitar|guitar)\b", text):
        traits.append("acousticGuitar")
    if re.search(r"\b(ambient|texture|textures|synth|electronic)\b", text):
        traits.extend(["ambient", "synth", "ethereal"])
    if re.search(r"\b(instrumental|no vocal|less vocal|without vocal|mostly instrumental)\b", text):
        traits.append("instrumental")
    if re.search(r"\b(slow|low energy|unhurried)\b", text):
        traits.extend(["slow", "low energy"])
    return list(dict.fromkeys(traits)) or ["reflective", "mediumSlow", "background"]


def _fallback_interpretation(request_text: str, profile_md: str, traits: list[str]) -> str:
    trait_text = ", ".join(traits[:6])
    profile_sentence = ""
    if profile_md.strip():
        profile_sentence = f" Your taste profile nudges this toward {_short_profile_hint(profile_md)}."
    if re.search(r"\b(work|working|focus|study|reading|background)\b", request_text, re.I):
        return (
            f"I'm translating this into music that can sit in the background: {trait_text}, "
            "with low distraction and a stable feel."
            f"{profile_sentence}"
        )
    return (
        f"I'm translating the notes into searchable Cyanite traits: {trait_text}. "
        "The goal is to match the sound and use case, not just reuse the words you typed."
        f"{profile_sentence}"
    )


def _fallback_soft_targets(traits: list[str]) -> list[dict]:
    dim_by_trait = {
        "calm": "mood",
        "peaceful": "mood",
        "quiet": "mood",
        "hopeful": "mood",
        "warm": "character",
        "cinematic": "musicFor",
        "focus": "musicFor",
        "background": "musicFor",
        "low energy": "energy",
        "steady movement": "movement",
        "instrumental": "vocals",
        "piano": "instrument",
        "acousticGuitar": "instrument",
        "slow": "tempo",
    }
    targets = []
    for trait in traits[:8]:
        dim = dim_by_trait.get(trait)
        if dim:
            targets.append({"dim": dim, "value": trait, "weight": 0.75})
    return targets


def _short_profile_hint(profile_md: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", profile_md)
    hint = " ".join(words[:14])
    hint = re.sub(r"\bUser often likes\b", "you often like", hint, flags=re.I)
    hint = re.sub(r"\bUser likes\b", "you like", hint, flags=re.I)
    return hint


def _extract_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                return text
    raise ValueError("OpenAI response did not contain output text")


def _normalize_query_card(raw: dict) -> dict:
    return {
        "interpretation_plain": str(raw.get("interpretation_plain", "")).strip(),
        "free_text_query": str(raw.get("free_text_query", "")).strip(),
        "soft_targets": [_normalize_soft_target(x) for x in raw.get("soft_targets", []) if isinstance(x, dict)],
        "negatives": [_normalize_negative(x) for x in raw.get("negatives", []) if isinstance(x, dict)],
    }


def _normalize_soft_target(raw: dict) -> dict:
    return {
        "dim": str(raw.get("dim", "")).strip(),
        "value": str(raw.get("value", "")).strip(),
        "weight": float(raw.get("weight", 0)),
    }


def _normalize_negative(raw: dict) -> dict:
    return {
        "dim": str(raw.get("dim", "")).strip(),
        "value": str(raw.get("value", "")).strip(),
    }
