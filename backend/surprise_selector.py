"""Select one prompt-relevant track that offers an explainable taste contrast."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable


TAG_DIMENSIONS = ("moods", "genres", "instruments", "character", "movement", "vocals")


@dataclass(frozen=True)
class SurpriseSelection:
    visible_cards: list[dict]
    backlog_cards: list[dict]
    metadata_by_id: dict[str, dict]


def select_surprise_recommendations(
    cards: list[dict],
    *,
    taste_track_ids: list[str],
    tag_loader: Callable[[str], dict],
    visible_n: int,
    force_one: bool = False,
    probability: float = 0.05,
    random_value: Callable[[], float] = random.random,
    candidate_limit: int = 5,
    prompt_score_ratio: float = 0.8,
) -> SurpriseSelection:
    """Return a visible list with at most one surprise and the remaining backlog.

    Production evaluates ``probability`` once per recommendation group. Demo mode
    bypasses that draw with ``force_one=True``.
    """
    prepared = [{**card, "is_surprise": False} for card in cards]
    visible = prepared[:visible_n]
    backlog = prepared[visible_n:]
    if not visible or (not force_one and random_value() >= probability):
        return SurpriseSelection(visible, backlog, {})

    candidates = backlog[:candidate_limit]
    if not candidates:
        candidates = visible[-1:]

    baseline_tags = _load_baseline(taste_track_ids, tag_loader)
    baseline_source = "historical_likes"
    if not baseline_tags:
        baseline_tags = _load_baseline(
            [card["cyanite_id"] for card in visible[:-1]], tag_loader
        )
        baseline_source = "current_prompt_cluster"

    score_floor = _score(visible[-1]) * prompt_score_ratio
    ranked = []
    for candidate in candidates:
        tags = _safe_load(tag_loader, candidate["cyanite_id"])
        if not tags or _score(candidate) < score_floor:
            continue
        shared, different = _compare_tags(baseline_tags, tags)
        if not shared or not different:
            continue
        contrast = len(different) / max(len(shared) + len(different), 1)
        ranked.append((contrast, _score(candidate), candidate, shared, different))

    if ranked:
        _, _, selected, shared, different = max(ranked, key=lambda item: (item[0], item[1]))
        basis = "cyanite_tag_contrast_with_prompt_guardrail"
    elif force_one:
        selected = max(candidates, key=_score)
        shared, different = [], []
        basis = "prompt_search_demo_fallback"
    else:
        return SurpriseSelection(visible, backlog, {})

    selected_id = selected["cyanite_id"]
    surprise_card = {**selected, "is_surprise": True}
    displaced = visible[-1]
    visible = visible[:-1] + [surprise_card]
    displaced_cards = [] if displaced["cyanite_id"] == selected_id else [displaced]
    backlog = displaced_cards + [card for card in backlog if card["cyanite_id"] != selected_id]
    metadata = {
        selected_id: {
            "is_surprise": True,
            "selection_basis": basis,
            "taste_baseline": baseline_source,
            "prompt_search_score": _score(selected),
            "shared_attributes": shared,
            "different_attributes": different,
        }
    }
    return SurpriseSelection(visible, backlog, metadata)


def _load_baseline(track_ids: list[str], tag_loader: Callable[[str], dict]) -> dict:
    baseline = {dimension: set() for dimension in TAG_DIMENSIONS}
    loaded = False
    for track_id in dict.fromkeys(track_ids[:3]):
        tags = _safe_load(tag_loader, track_id)
        if not tags:
            continue
        loaded = True
        for dimension in TAG_DIMENSIONS:
            baseline[dimension].update(tags.get(dimension) or [])
    return baseline if loaded else {}


def _compare_tags(baseline: dict, candidate: dict) -> tuple[list[str], list[str]]:
    shared = []
    different = []
    for dimension in TAG_DIMENSIONS:
        baseline_values = set(baseline.get(dimension) or [])
        candidate_values = set(candidate.get(dimension) or [])
        shared.extend(f"{dimension}:{value}" for value in sorted(candidate_values & baseline_values))
        different.extend(f"{dimension}:{value}" for value in sorted(candidate_values - baseline_values))
    return shared, different


def _safe_load(tag_loader: Callable[[str], dict], track_id: str) -> dict:
    try:
        return tag_loader(track_id) or {}
    except Exception:
        return {}


def _score(card: dict) -> float:
    value = card.get("score")
    return float(value) if isinstance(value, int | float) else 0.0
