import user_profiles


def test_liked_cyanite_ids_reads_provided_user_profile():
    liked = user_profiles.liked_cyanite_ids("545127")

    assert liked
    assert all(track_id.startswith("libtr_") for track_id in liked)


def test_liked_cyanite_ids_returns_empty_for_unknown_user():
    assert user_profiles.liked_cyanite_ids("__missing__") == []
