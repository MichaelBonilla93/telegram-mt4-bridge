from src.dedup import SeenStore


def test_marks_and_detects_seen(tmp_path):
    store = SeenStore(str(tmp_path / "seen.json"))
    assert store.seen(101) is False
    store.mark(101)
    assert store.seen(101) is True


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "seen.json")
    s1 = SeenStore(path)
    s1.mark(202)
    s2 = SeenStore(path)
    assert s2.seen(202) is True
