import os
import types
import config
from datetime import datetime, timezone
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


def _fake_io(scenes_light, performers):
    return types.SimpleNamespace(
        fetch_scenes_light=lambda s: scenes_light,
        fetch_performers=lambda s: performers,
        utcnow=lambda: datetime(2026, 6, 15, tzinfo=timezone.utc))


def test_restore_targets_restores_and_clears():
    # backup had scene 1 = 80; library now: 1 overwritten to 95, 2 mirror-applied (88)
    targets = rb._restore_targets({"1": 80}, {"1": 95, "2": 88})
    assert targets == {"1": 80, "2": None}

def test_restore_targets_skips_already_correct():
    targets = rb._restore_targets({"1": 80}, {"1": 80, "2": None})
    assert targets == {}   # 1 already correct, 2 already null


def test_run_backup_collects_and_writes(monkeypatch, tmp_path):
    p = str(tmp_path / "b.json")
    monkeypatch.setattr(rb, "default_backup_path", lambda: p)
    monkeypatch.setattr(rb, "stash_io", _fake_io(
        [{"id": "1", "rating100": 80}, {"id": "2", "rating100": None}],
        [_perf("9", 50)]))
    assert rb.run_backup("STASH", config.Settings()) == 0
    data = rb.load_backup(p)
    assert data["scenes"] == {"1": 80} and data["performers"] == {"9": 50}


def test_run_restore_missing_backup_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(rb, "default_backup_path", lambda: str(tmp_path / "nope.json"))
    assert rb.run_restore("STASH", config.Settings()) == 1


def test_run_restore_restores_and_clears(monkeypatch, tmp_path):
    p = str(tmp_path / "b.json")
    rb.write_backup(p, scenes={"1": 80}, performers={}, written_at="t", rotate=False)
    monkeypatch.setattr(rb, "default_backup_path", lambda: p)
    monkeypatch.setattr(rb, "stash_io", _fake_io(
        [{"id": "1", "rating100": 95}, {"id": "2", "rating100": 88}], []))
    calls = {}
    def fake_write_ratings(stash, entity, id_to_rating, cfg):
        calls[entity] = dict(id_to_rating)
        return {"written": len(id_to_rating), "failed": 0}
    monkeypatch.setattr(rb, "writer", types.SimpleNamespace(write_ratings=fake_write_ratings))
    assert rb.run_restore("STASH", config.Settings()) == 0
    assert calls["scene"] == {"1": 80, "2": None}   # 1 restored, 2 cleared


def test_run_restore_nonzero_when_writes_fail(monkeypatch, tmp_path):
    p = str(tmp_path / "b.json")
    rb.write_backup(p, scenes={"1": 80}, performers={}, written_at="t", rotate=False)
    monkeypatch.setattr(rb, "default_backup_path", lambda: p)
    monkeypatch.setattr(rb, "stash_io", _fake_io([{"id": "1", "rating100": 95}], []))
    monkeypatch.setattr(rb, "writer", types.SimpleNamespace(
        write_ratings=lambda *a, **k: {"written": 0, "failed": 1}))
    assert rb.run_restore("STASH", config.Settings()) == 1
