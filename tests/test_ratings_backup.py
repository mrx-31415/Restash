import os
import types
import ratings_backup as rb


def _scene(i, r):
    return {"id": i, "rating100": r}


def _perf(i, r):
    return types.SimpleNamespace(id=i, rating100=r)


def test_collect_ratings_keeps_only_non_null():
    sc, pf = rb.collect_ratings([_scene("1", 80), _scene("2", None)],
                                [_perf("9", 50), _perf("8", None)])
    assert sc == {"1": 80} and pf == {"9": 50}


def test_write_and_load_roundtrip(tmp_path):
    p = str(tmp_path / "b.json")
    rb.write_backup(p, scenes={"1": 80}, performers={"9": 50},
                    written_at="2026-06-15T00:00:00Z", rotate=False)
    data = rb.load_backup(p)
    assert data["scenes"] == {"1": 80}
    assert data["performers"] == {"9": 50}
    assert data["format_version"] == rb.BACKUP_FORMAT_VERSION


def test_write_backup_rotates_existing(tmp_path):
    p = str(tmp_path / "b.json")
    rb.write_backup(p, scenes={"1": 1}, performers={}, written_at="t1", rotate=False)
    rotated = rb.write_backup(p, scenes={"1": 2}, performers={}, written_at="t2", rotate=True)
    assert rotated and os.path.exists(rotated)
    assert rb.load_backup(rotated)["scenes"] == {"1": 1}   # old snapshot preserved
    assert rb.load_backup(p)["scenes"] == {"1": 2}          # canonical is newest


def test_write_backup_no_rotate_overwrites(tmp_path):
    p = str(tmp_path / "b.json")
    rb.write_backup(p, scenes={"1": 1}, performers={}, written_at="t1", rotate=False)
    rotated = rb.write_backup(p, scenes={"1": 2}, performers={}, written_at="t2", rotate=False)
    assert rotated == ""
    assert rb.load_backup(p)["scenes"] == {"1": 2}


def test_load_backup_missing_or_corrupt(tmp_path):
    assert rb.load_backup(str(tmp_path / "nope.json")) is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert rb.load_backup(str(bad)) is None
    incomplete = tmp_path / "inc.json"
    incomplete.write_text('{"format_version": 1}')   # missing scenes/performers
    assert rb.load_backup(str(incomplete)) is None


def test_backup_exists(tmp_path):
    p = str(tmp_path / "b.json")
    assert rb.backup_exists(p) is False
    rb.write_backup(p, scenes={}, performers={}, written_at="t", rotate=False)
    assert rb.backup_exists(p) is True
