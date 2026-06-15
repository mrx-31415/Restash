import types
import restash as entry
import config

def test_parse_input_extracts_mode_conn_and_args():
    payload = {"server_connection": {"Scheme": "http"}, "args": {"mode": "dry"}}
    mode, conn, args = entry.parse_input(payload)
    assert mode == "dry"
    assert conn == {"Scheme": "http"}
    assert args == {"mode": "dry"}

def test_parse_input_defaults_mode_to_dry():
    mode, _, _ = entry.parse_input({})
    assert mode == "dry"

def test_build_settings_applies_plugin_config():
    s = entry.build_settings({"cooldownDays": 7}, {})
    assert s.cooldown_days == 7.0
    assert s.wildcard_percent == 2.0   # untouched key keeps default

def test_run_dispatches_dry(monkeypatch):
    captured = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True,
                                 "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {},
    )
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "_run_dry",
                        lambda stash, settings: captured.setdefault("dry", True) and 0)
    rc = entry.run({"args": {"mode": "dry"}})
    assert rc == 0 and captured.get("dry") is True

def test_run_dispatches_full(monkeypatch):
    captured = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {})
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "_run_full",
                        lambda stash, settings: captured.setdefault("full", True) and 0)
    assert entry.run({"args": {"mode": "full"}}) == 0 and captured["full"] is True

def test_run_dispatches_clear(monkeypatch):
    captured = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {})
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "_run_clear",
                        lambda stash, settings: captured.setdefault("clear", True) and 0)
    assert entry.run({"args": {"mode": "clear"}}) == 0 and captured["clear"] is True

def test_build_settings_reads_write_limit_from_args():
    s = entry.build_settings(None, {"mode": "full", "write_limit": 5})
    assert s.write_limit == 5

def test_build_settings_reads_scene_ids_from_args():
    s = entry.build_settings(None, {"mode": "full", "scene_ids": [10, "22"]})
    assert s.write_only_scene_ids == ("10", "22")

def test_run_reads_settings_from_server(monkeypatch):
    seen = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {"cooldownDays": 5})
    def cap(stash, settings):
        seen["cd"] = settings.cooldown_days
        return 0
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "_run_dry", cap)
    assert entry.run({"args": {"mode": "dry"}}) == 0
    assert seen["cd"] == 5.0   # server-configured setting actually took effect

def test_run_payload_plugin_config_overrides_server(monkeypatch):
    seen = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {"cooldownDays": 5})
    def cap(stash, settings):
        seen["cd"] = settings.cooldown_days
        return 0
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "_run_dry", cap)
    rc = entry.run({"args": {"mode": "dry"}, "plugin_config": {"cooldownDays": 9}})
    assert rc == 0 and seen["cd"] == 9.0

def test_run_full_targeted_writes_only_named_scenes(monkeypatch):
    import types
    calls = []
    Scene = lambda i: types.SimpleNamespace(id=i, custom_fields={}, favorite=False, rating100=None)
    fake_scenes = [Scene("1"), Scene("2"), Scene("3")]
    fake_perfs = [types.SimpleNamespace(id="9", custom_fields={}, favorite=False, rating100=None)]
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes=lambda s: fake_scenes,
        fetch_performers=lambda s: fake_perfs,
        resolve_tag_id=lambda s, n: None,
        filter_excluded=lambda sc, pf, ex: (sc, pf))
    fake_algo = types.SimpleNamespace(
        build_affinities=lambda *a, **k: {},
        score_scenes=lambda *a, **k: {"1": object(), "2": object(), "3": object()},
        score_performers=lambda *a, **k: {"9": object()})
    clear_calls = []
    def fake_write_scores(stash, entity, scored, existing, cfg, now_iso):
        calls.append((entity, sorted(scored.keys())))
        return {"written": len(scored), "skipped": 0, "would_write": len(scored)}
    fake_writer = types.SimpleNamespace(
        write_scores=fake_write_scores,
        clear_scores=lambda stash, entity, ids, cfg: clear_calls.append((entity, ids)) or 0,
        RESTASH_KEYS=entry.writer.RESTASH_KEYS)
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", fake_writer)
    monkeypatch.setattr(entry, "_build_scene_cache", lambda *a, **k: {})
    monkeypatch.setattr(entry, "state", types.SimpleNamespace(
        default_state_path=lambda: "/tmp/ignored.json",
        save_state=lambda *a, **k: None))
    rc = entry._run_full("STASH", config.Settings(write_only_scene_ids=("2",)))
    assert rc == 0
    assert ("scene", ["2"]) in calls       # only the targeted scene written
    assert ("performer", []) in calls       # performers skipped in targeted mode
    # D8 must be bypassed in targeted mode: clear_scores only ever gets empty id lists
    assert all(ids == [] for _, ids in clear_calls)


def test_run_full_returns_nonzero_when_writes_fail(monkeypatch):
    import types
    Scene = lambda i: types.SimpleNamespace(id=i, custom_fields={}, favorite=False, rating100=None)
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes=lambda s: [Scene("1"), Scene("2")],
        fetch_performers=lambda s: [],
        resolve_tag_id=lambda s, n: None,
        filter_excluded=lambda sc, pf, ex: (sc, pf))
    fake_algo = types.SimpleNamespace(
        build_affinities=lambda *a, **k: {},
        score_scenes=lambda *a, **k: {"1": object(), "2": object()},
        score_performers=lambda *a, **k: {})
    fake_writer = types.SimpleNamespace(
        write_scores=lambda *a, **k: {"written": 1, "skipped": 0, "would_write": 2, "failed": 1},
        clear_scores=lambda *a, **k: 0,
        RESTASH_KEYS=entry.writer.RESTASH_KEYS)
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", fake_writer)
    monkeypatch.setattr(entry, "_build_scene_cache", lambda *a, **k: {})
    monkeypatch.setattr(entry, "state", types.SimpleNamespace(
        default_state_path=lambda: "/tmp/ignored.json",
        save_state=lambda *a, **k: None))
    assert entry._run_full("STASH", config.Settings()) == 1   # a rejected write → non-zero exit


def test_run_full_persists_cache(monkeypatch):
    import types
    from datetime import datetime, timezone
    created = datetime(2025, 1, 1, tzinfo=timezone.utc)
    Scene = lambda i: types.SimpleNamespace(
        id=i, custom_fields={}, favorite=False, rating100=None,
        created_at=created, performer_ids=["9"])
    fake_scenes = [Scene("1"), Scene("2")]
    Score = lambda b, n: types.SimpleNamespace(components={"base": b}, n_events=n)
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes=lambda s: fake_scenes,
        fetch_performers=lambda s: [],
        resolve_tag_id=lambda s, n: None,
        filter_excluded=lambda sc, pf, ex: (sc, pf))
    fake_algo = types.SimpleNamespace(
        build_affinities=lambda *a, **k: {"performers": {"9": 0.4}},
        score_scenes=lambda *a, **k: {"1": Score(0.2, 0), "2": Score(0.3, 5)},
        score_performers=lambda *a, **k: {},
        _last_engagement=lambda s: None)
    captured = {}
    fake_state = types.SimpleNamespace(
        default_state_path=lambda: "/tmp/ignored.json",
        save_state=lambda path, **kw: captured.update(kw))
    fake_writer = types.SimpleNamespace(
        write_scores=lambda *a, **k: {"written": 0, "skipped": 0, "would_write": 0, "failed": 0},
        clear_scores=lambda *a, **k: 0, RESTASH_KEYS=entry.writer.RESTASH_KEYS)
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", fake_writer)
    monkeypatch.setattr(entry, "state", fake_state)
    rc = entry._run_full("STASH", config.Settings())
    assert rc == 0
    assert captured["affinities"] == {"performers": {"9": 0.4}}
    assert captured["scenes"]["1"]["base"] == 0.2
    assert captured["scenes"]["2"]["n_events"] == 5
    assert captured["scenes"]["1"]["perf_ids"] == ["9"]


def test_run_clear_returns_nonzero_when_clears_fail(monkeypatch):
    import types
    Scene = lambda i: types.SimpleNamespace(id=i, custom_fields={"restash_score": 5})
    fake_io = types.SimpleNamespace(
        fetch_scenes=lambda s: [Scene("1"), Scene("2"), Scene("3")],
        fetch_performers=lambda s: [])
    # 3 scenes carry restash_* but the server only acknowledges 2 removals
    fake_writer = types.SimpleNamespace(
        clear_scores=lambda stash, entity, ids, cfg: (2 if ids else 0),
        RESTASH_KEYS=entry.writer.RESTASH_KEYS)
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "writer", fake_writer)
    assert entry._run_clear("STASH", config.Settings()) == 1   # 3 attempted, 2 cleared → non-zero


def test_run_dispatches_refresh(monkeypatch):
    captured = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {})
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "_run_refresh",
                        lambda stash, settings: captured.setdefault("refresh", True) and 0)
    assert entry.run({"args": {"mode": "refresh"}}) == 0 and captured["refresh"] is True


def test_run_refresh_self_heals_when_cache_invalid(monkeypatch):
    import types
    fake_state = types.SimpleNamespace(
        default_state_path=lambda: "/tmp/x.json",
        load_state=lambda p: None,
        is_valid=lambda st, cfg: (False, "no cache file (missing or unreadable)"))
    monkeypatch.setattr(entry, "state", fake_state)
    healed = {}
    monkeypatch.setattr(entry, "_run_full",
                        lambda stash, settings: healed.setdefault("full", True) and 0)
    rc = entry._run_refresh("STASH", config.Settings())
    assert rc == 0 and healed.get("full") is True


def test_run_refresh_writes_from_cache(monkeypatch):
    import types
    from datetime import datetime, timezone
    cached_scenes = {"1": {"base": 0.2, "n_events": 0,
                           "created_at": "2025-01-01T00:00:00Z",
                           "last_engagement": None, "perf_ids": ["9"]}}
    fake_state = types.SimpleNamespace(
        default_state_path=lambda: "/tmp/x.json",
        load_state=lambda p: {"scenes": cached_scenes,
                              "affinities": {"performers": {"9": 0.4}}},
        is_valid=lambda st, cfg: (True, "ok"))
    light = [{"id": "1", "last_played_at": None, "play_count": 0,
              "o_counter": 0, "custom_fields": {}}]
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes_light=lambda s: light,
        fetch_performers=lambda s: [],
        _parse_dt=entry.stash_io._parse_dt)
    Score = lambda: types.SimpleNamespace(restash_score=50)
    fake_algo = types.SimpleNamespace(
        refresh_scene_scores=lambda *a, **k: {"1": Score()},
        score_performers=lambda *a, **k: {},
        _max_dt=entry.algorithm._max_dt)
    calls = []
    fake_writer = types.SimpleNamespace(
        write_scores=lambda stash, entity, scored, existing, cfg, now_iso:
            calls.append(entity) or {"written": len(scored), "skipped": 0,
                                      "would_write": len(scored), "failed": 0},
        RESTASH_KEYS=entry.writer.RESTASH_KEYS)
    monkeypatch.setattr(entry, "state", fake_state)
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", fake_writer)
    rc = entry._run_refresh("STASH", config.Settings())
    assert rc == 0
    assert "scene" in calls and "performer" in calls


def test_run_refresh_mirror_autobackups_and_passes_current_ratings(monkeypatch):
    import types
    cached_scenes = {"1": {"base": 0.2, "n_events": 0,
                           "created_at": "2025-01-01T00:00:00Z",
                           "last_engagement": None, "perf_ids": []},
                     "2": {"base": 0.3, "n_events": 0,
                           "created_at": "2025-01-01T00:00:00Z",
                           "last_engagement": None, "perf_ids": []}}
    fake_state = types.SimpleNamespace(
        default_state_path=lambda: "/tmp/x.json",
        load_state=lambda p: {"scenes": cached_scenes,
                              "affinities": {"performers": {}}},
        is_valid=lambda st, cfg: (True, "ok"))
    # Scene "1" has a non-null rating, "2" is None; "3" is a light-only scene
    # (non-null rating) that is not scored — exercises the id-set divergence.
    light = [{"id": "1", "rating100": 95, "custom_fields": {}},
             {"id": "2", "rating100": None, "custom_fields": {}},
             {"id": "3", "rating100": 60, "custom_fields": {}}]
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes_light=lambda s: light,
        fetch_performers=lambda s: [],
        _parse_dt=entry.stash_io._parse_dt)
    Score = lambda: types.SimpleNamespace(restash_score=50)
    fake_algo = types.SimpleNamespace(
        # scored subset = {"1", "2"} (not "3")
        refresh_scene_scores=lambda *a, **k: {"1": Score(), "2": Score()},
        score_performers=lambda *a, **k: {},
        _max_dt=entry.algorithm._max_dt)
    seen = {}
    def fake_write_scores(stash, entity, scored, existing, cfg, now_iso, current_ratings=None):
        seen[entity] = current_ratings
        return {"written": len(scored), "skipped": 0,
                "would_write": len(scored), "failed": 0}
    backup_calls = {}
    fake_rb = types.SimpleNamespace(
        default_backup_path=lambda: "/tmp/ignored-backup.json",
        backup_exists=lambda p: False,
        write_backup=lambda path, **kw: backup_calls.update(kw) or "")
    monkeypatch.setattr(entry, "state", fake_state)
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", types.SimpleNamespace(
        write_scores=fake_write_scores, RESTASH_KEYS=entry.writer.RESTASH_KEYS))
    monkeypatch.setattr(entry, "ratings_backup", fake_rb)
    rc = entry._run_refresh("STASH", config.Settings(mirror_to_rating100=True))
    assert rc == 0
    # auto-backup iterates ALL light scenes, keeping only non-null ratings (incl. unscored "3")
    assert backup_calls["scenes"] == {"1": 95, "3": 60}
    # current_ratings is keyed by the scored subset only ({"1","2"}), not "3"
    assert seen["scene"] == {"1": 95, "2": None}


def test_run_dispatches_backup_ratings(monkeypatch):
    captured = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {})
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "ratings_backup", types.SimpleNamespace(
        run_backup=lambda stash, settings: captured.setdefault("backup", True) and 0,
        run_restore=lambda stash, settings: 0))
    assert entry.run({"args": {"mode": "backup-ratings"}}) == 0
    assert captured["backup"] is True

def test_run_dispatches_restore_ratings(monkeypatch):
    captured = {}
    fake_io = types.SimpleNamespace(
        connect=lambda c: "STASH",
        ensure_schema=lambda s: {"scene_custom_fields": True, "custom_fields_remove": True},
        fetch_plugin_settings=lambda s, pid: {})
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "ratings_backup", types.SimpleNamespace(
        run_backup=lambda stash, settings: 0,
        run_restore=lambda stash, settings: captured.setdefault("restore", True) and 0))
    assert entry.run({"args": {"mode": "restore-ratings"}}) == 0
    assert captured["restore"] is True

def test_run_full_mirror_autobackups_and_passes_current_ratings(monkeypatch):
    import types
    from datetime import datetime, timezone
    created = datetime(2025, 1, 1, tzinfo=timezone.utc)
    Scene = lambda i, r: types.SimpleNamespace(
        id=i, custom_fields={}, favorite=False, rating100=r,
        created_at=created, performer_ids=[])
    fake_scenes = [Scene("1", 95), Scene("2", None)]
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes=lambda s: fake_scenes,
        fetch_performers=lambda s: [],
        resolve_tag_id=lambda s, n: None,
        filter_excluded=lambda sc, pf, ex: (sc, pf))
    fake_algo = types.SimpleNamespace(
        build_affinities=lambda *a, **k: {},
        score_scenes=lambda *a, **k: {"1": types.SimpleNamespace(restash_score=80),
                                      "2": types.SimpleNamespace(restash_score=70)},
        score_performers=lambda *a, **k: {},
        _last_engagement=lambda s: None)
    seen = {}
    def fake_write_scores(stash, entity, scored, existing, cfg, now_iso, current_ratings=None):
        seen[entity] = current_ratings
        return {"written": 0, "skipped": 0, "would_write": 0, "failed": 0}
    backup_calls = {}
    fake_rb = types.SimpleNamespace(
        default_backup_path=lambda: "/tmp/ignored-backup.json",
        backup_exists=lambda p: False,
        write_backup=lambda path, **kw: backup_calls.update(kw) or "")
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", types.SimpleNamespace(
        write_scores=fake_write_scores,
        clear_scores=lambda *a, **k: 0, RESTASH_KEYS=entry.writer.RESTASH_KEYS))
    monkeypatch.setattr(entry, "ratings_backup", fake_rb)
    monkeypatch.setattr(entry, "_build_scene_cache", lambda *a, **k: {})
    monkeypatch.setattr(entry, "state", types.SimpleNamespace(
        default_state_path=lambda: "/tmp/ignored.json", save_state=lambda *a, **k: None))
    rc = entry._run_full("STASH", config.Settings(mirror_to_rating100=True))
    assert rc == 0
    # auto-backup captured only the non-null original rating
    assert backup_calls["scenes"] == {"1": 95}
    # write_scores received current ratings for the mirror skip (incl the None)
    assert seen["scene"] == {"1": 95, "2": None}

def test_run_full_no_mirror_does_not_autobackup(monkeypatch):
    import types
    from datetime import datetime, timezone
    created = datetime(2025, 1, 1, tzinfo=timezone.utc)
    Scene = lambda i: types.SimpleNamespace(
        id=i, custom_fields={}, favorite=False, rating100=50,
        created_at=created, performer_ids=[])
    fake_io = types.SimpleNamespace(
        utcnow=entry.stash_io.utcnow,
        fetch_scenes=lambda s: [Scene("1")],
        fetch_performers=lambda s: [],
        resolve_tag_id=lambda s, n: None,
        filter_excluded=lambda sc, pf, ex: (sc, pf))
    fake_algo = types.SimpleNamespace(
        build_affinities=lambda *a, **k: {},
        score_scenes=lambda *a, **k: {"1": types.SimpleNamespace(restash_score=80)},
        score_performers=lambda *a, **k: {}, _last_engagement=lambda s: None)
    seen = {}
    def fake_write_scores(stash, entity, scored, existing, cfg, now_iso, current_ratings=None):
        seen[entity] = current_ratings
        return {"written": 0, "skipped": 0, "would_write": 0, "failed": 0}
    exists_checked = {"n": 0}
    fake_rb = types.SimpleNamespace(
        default_backup_path=lambda: "/tmp/x.json",
        backup_exists=lambda p: exists_checked.__setitem__("n", exists_checked["n"] + 1) or True,
        write_backup=lambda *a, **k: "")
    monkeypatch.setattr(entry, "stash_io", fake_io)
    monkeypatch.setattr(entry, "algorithm", fake_algo)
    monkeypatch.setattr(entry, "writer", types.SimpleNamespace(
        write_scores=fake_write_scores, clear_scores=lambda *a, **k: 0,
        RESTASH_KEYS=entry.writer.RESTASH_KEYS))
    monkeypatch.setattr(entry, "ratings_backup", fake_rb)
    monkeypatch.setattr(entry, "_build_scene_cache", lambda *a, **k: {})
    monkeypatch.setattr(entry, "state", types.SimpleNamespace(
        default_state_path=lambda: "/tmp/ignored.json", save_state=lambda *a, **k: None))
    rc = entry._run_full("STASH", config.Settings())   # mirror off
    assert rc == 0
    assert seen["scene"] is None        # off-path passes no current_ratings
    assert exists_checked["n"] == 0     # auto-backup never consulted when mirror off

def test_manual_ratings_off_returns_empty():
    s = config.Settings(respect_manual_ratings=False)
    assert entry._manual_ratings(s, live_scene={"1": 80}, live_perf={"9": 50}) == ({}, {})

def test_manual_ratings_live_when_mirror_off():
    s = config.Settings(respect_manual_ratings=True)   # mirror off
    assert entry._manual_ratings(s, live_scene={"1": 80}, live_perf={"9": 50}) \
        == ({"1": 80}, {"9": 50})

def test_manual_ratings_from_backup_when_mirror_on(monkeypatch):
    s = config.Settings(respect_manual_ratings=True, mirror_to_rating100=True)
    monkeypatch.setattr(entry, "ratings_backup", types.SimpleNamespace(
        default_backup_path=lambda: "/tmp/x.json",
        load_backup=lambda p: {"scenes": {"1": 10}, "performers": {"9": 20}}))
    # originals from backup, NOT the polluted live field (anti-feedback-loop, D21)
    assert entry._manual_ratings(s, live_scene={"1": 80}, live_perf={"9": 50}) \
        == ({"1": 10}, {"9": 20})

def test_manual_ratings_live_when_mirror_on_but_no_backup(monkeypatch):
    s = config.Settings(respect_manual_ratings=True, mirror_to_rating100=True)
    monkeypatch.setattr(entry, "ratings_backup", types.SimpleNamespace(
        default_backup_path=lambda: "/tmp/x.json", load_backup=lambda p: None))
    # first mirror run: no backup yet, live field still pristine
    assert entry._manual_ratings(s, live_scene={"1": 80}, live_perf={"9": 50}) \
        == ({"1": 80}, {"9": 50})
