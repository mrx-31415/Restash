# Scheduling

Stash has **no built-in scheduler for plugin tasks**, so run **Quick Refresh** on a schedule from
outside Stash. Quick Refresh is the cheap daily job: it re-applies freshness, novelty, jitter, and
wildcards from the cached taste model (written by **Recompute All**) without rebuilding affinities.
If the cache is missing or stale it self-heals by running a full recompute. Expect a daily refresh
to skip most scenes as unchanged (performers churn a bit more — see the
[determinism note](how-it-works.md#a-note-on-determinism)); that is normal and correct.

Trigger it via the GraphQL `runPluginTask` mutation. A ready-to-use helper lives in
[`scripts/restash-refresh.sh`](https://github.com/Espionage9248/Restash/blob/main/scripts/restash-refresh.sh):

```bash
STASH_URL=http://localhost:9999 ./scripts/restash-refresh.sh
# with auth enabled:
STASH_URL=http://host:9999 STASH_API_KEY=xxxx ./scripts/restash-refresh.sh
```

## cron

```cron
0 4 * * * STASH_URL=http://localhost:9999 /opt/restash/scripts/restash-refresh.sh >> /var/log/restash-refresh.log 2>&1
```

## systemd timer

Copy
[`scripts/restash-refresh.service`](https://github.com/Espionage9248/Restash/blob/main/scripts/restash-refresh.service)
and
[`scripts/restash-refresh.timer`](https://github.com/Espionage9248/Restash/blob/main/scripts/restash-refresh.timer)
to `/etc/systemd/system/` (edit the `ExecStart` path and `STASH_URL`/`STASH_API_KEY`), then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now restash-refresh.timer
systemctl list-timers restash-refresh.timer
```

The underlying mutation (for reference):

```graphql
mutation { runPluginTask(plugin_id: "restash", task_name: "Quick Refresh") }
```

!!! note "Heads-up on a scheduled run"
    Each entity a refresh writes is a Stash update, which fires Stash's update hooks — so other
    update-hook plugins run too. Steady-state daily refreshes write few entities (unchanged ones are
    skipped), so this is usually negligible, but it's worth knowing before automating. See
    [Writing triggers other plugins' update hooks](usage.md#update-hooks).
