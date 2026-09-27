from robosidelink.randomness import NamedRandomStreams


def test_same_root_seed_and_name_reproduce_sequence() -> None:
    first = NamedRandomStreams(42).rng("traffic:0")
    second = NamedRandomStreams(42).rng("traffic:0")

    assert [first.random() for _ in range(4)] == [second.random() for _ in range(4)]


def test_different_stream_names_produce_different_sequences() -> None:
    streams = NamedRandomStreams(42)

    traffic = [streams.rng("traffic:0").random() for _ in range(4)]
    selector = [streams.rng("selector:0").random() for _ in range(4)]

    assert traffic != selector


def test_consuming_one_stream_does_not_change_another() -> None:
    used = NamedRandomStreams(42)
    untouched = NamedRandomStreams(42)

    for _ in range(10):
        used.rng("traffic:0").random()

    assert used.rng("selector:0").random() == untouched.rng("selector:0").random()


def test_repeated_name_returns_cached_generator() -> None:
    streams = NamedRandomStreams(42)

    assert streams.rng("selector:0") is streams.rng("selector:0")


def test_negative_root_seed_is_rejected() -> None:
    try:
        NamedRandomStreams(-1)
    except ValueError as error:
        assert "root_seed" in str(error)
    else:
        raise AssertionError("negative root seed was accepted")
