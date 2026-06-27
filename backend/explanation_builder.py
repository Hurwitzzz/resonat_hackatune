"""接缝 · 推荐解释生成。

把用户画像、当前 Query Card、liked/recommended 曲目的 Cyanite tags 和排序元数据
合成英文 Why this track 文本。业务层可以直接 import 本模块；这里不接 FastAPI。
"""
from __future__ import annotations

import json

import requests

import config


SYSTEM_PROMPT = """You explain music recommendations in English.

Ground every claim in the supplied Cyanite tags, Query Card, user profile, or ranking metadata.
Do not invent genres, moods, instruments, BPM, user behavior, or popularity signals.
Explain:
1. how the track fits the current prompt,
2. how it relates to the listener's taste,
3. why it was selected from the recommendation path.

Keep why_text concise: 2-4 sentences, user-facing, non-technical unless the evidence needs a tag name.
"""

EXPLANATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["why_text", "evidence"],
    "properties": {
        "why_text": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "detail"],
                "properties": {
                    "source": {"type": "string"},
                    "detail": {"type": "string"},
                },
            },
        },
    },
}


def build_explanation(profile_md: str,
                      query_card: dict,
                      liked_track_tags: dict,
                      recommended_track_tags: dict,
                      recommendation_meta: dict) -> dict:
    """Return an English explanation grounded in provided Cyanite/user evidence."""
    if not config.OPENAI_API_KEY:
        return _fallback_explanation(query_card, recommendation_meta)
    return _explanation_from_openai(
        profile_md,
        query_card,
        liked_track_tags,
        recommended_track_tags,
        recommendation_meta,
    )


def _explanation_from_openai(profile_md: str,
                             query_card: dict,
                             liked_track_tags: dict,
                             recommended_track_tags: dict,
                             recommendation_meta: dict) -> dict:
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
                "content": [{
                    "type": "input_text",
                    "text": _build_user_prompt(
                        profile_md,
                        query_card,
                        liked_track_tags,
                        recommended_track_tags,
                        recommendation_meta,
                    ),
                }],
            }],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "recommendation_explanation",
                    "strict": True,
                    "schema": EXPLANATION_SCHEMA,
                }
            },
        },
        timeout=config.OPENAI_TIMEOUT,
    )
    response.raise_for_status()
    return _normalize_explanation(json.loads(_extract_output_text(response.json())))


def _build_user_prompt(profile_md: str,
                       query_card: dict,
                       liked_track_tags: dict,
                       recommended_track_tags: dict,
                       recommendation_meta: dict) -> str:
    payload = {
        "user_profile": profile_md.strip() or "(none yet)",
        "query_card": query_card,
        "liked_track_cyanite_tags": liked_track_tags,
        "recommended_track_cyanite_tags": recommended_track_tags,
        "recommendation_meta": recommendation_meta,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _fallback_explanation(query_card: dict, recommendation_meta: dict) -> dict:
    query = query_card.get("free_text_query") or query_card.get("interpretation_plain") or "your current search"
    score = recommendation_meta.get("final_score", recommendation_meta.get("similar_score"))
    score_text = f" with score {score:.2f}" if isinstance(score, int | float) else ""
    return {
        "why_text": (
            f"This track fits your current search for {query}. "
            f"It was selected from music near your liked tracks using Cyanite acoustic similarity{score_text}."
        ),
        "evidence": [{
            "source": "ranking",
            "detail": f"ranking_basis={recommendation_meta.get('ranking_basis', 'similar_score_fallback')}",
        }],
    }


def _extract_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                return text
    raise ValueError("OpenAI response did not contain output text")


def _normalize_explanation(raw: dict) -> dict:
    return {
        "why_text": str(raw.get("why_text", "")).strip(),
        "evidence": [_normalize_evidence(x) for x in raw.get("evidence", []) if isinstance(x, dict)],
    }


def _normalize_evidence(raw: dict) -> dict:
    return {
        "source": str(raw.get("source", "")).strip(),
        "detail": str(raw.get("detail", "")).strip(),
    }
