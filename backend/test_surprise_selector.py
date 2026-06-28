import surprise_selector


def _card(track_id: str, score: float) -> dict:
    return {"cyanite_id": track_id, "score": score, "is_surprise": False}


TAGS = {
    "liked": {"moods": ["calm"], "genres": ["classical"], "instruments": ["piano"]},
    "normal": {"moods": ["calm"], "genres": ["classical"], "instruments": ["piano"]},
    "bridge": {"moods": ["calm"], "genres": ["electronic"], "instruments": ["synth"]},
    "alien": {"moods": ["aggressive"], "genres": ["metal"], "instruments": ["electricGuitar"]},
}


def test_demo_list_contains_exactly_one_explainable_surprise():
    cards = [_card("normal", 1.0 - index / 100) for index in range(5)]
    cards += [_card("bridge", 0.93), _card("alien", 0.92)]

    result = surprise_selector.select_surprise_recommendations(
        cards,
        taste_track_ids=["liked"],
        tag_loader=lambda track_id: TAGS[track_id],
        visible_n=5,
        force_one=True,
    )

    assert len(result.visible_cards) == 5
    assert [card["cyanite_id"] for card in result.visible_cards][-1] == "bridge"
    assert sum(card["is_surprise"] for card in result.visible_cards) == 1
    assert result.metadata_by_id["bridge"]["shared_attributes"] == ["moods:calm"]
    assert "genres:electronic" in result.metadata_by_id["bridge"]["different_attributes"]
    assert result.backlog_cards[0]["cyanite_id"] == "normal"


def test_production_probability_is_applied_once_per_recommendation_group():
    cards = [_card("normal", 1.0 - index / 100) for index in range(5)] + [_card("bridge", 0.93)]

    result = surprise_selector.select_surprise_recommendations(
        cards,
        taste_track_ids=["liked"],
        tag_loader=lambda track_id: TAGS[track_id],
        visible_n=5,
        probability=0.05,
        random_value=lambda: 0.051,
    )

    assert not any(card["is_surprise"] for card in result.visible_cards)
    assert result.metadata_by_id == {}


def test_production_skips_surprise_when_no_candidate_bridges_taste_and_prompt():
    cards = [_card("normal", 1.0 - index / 100) for index in range(5)] + [_card("alien", 0.93)]

    result = surprise_selector.select_surprise_recommendations(
        cards,
        taste_track_ids=["liked"],
        tag_loader=lambda track_id: TAGS[track_id],
        visible_n=5,
        probability=0.05,
        random_value=lambda: 0.01,
    )

    assert not any(card["is_surprise"] for card in result.visible_cards)

