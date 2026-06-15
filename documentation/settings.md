# Settings

Exposed under **Settings → Plugins → Restash**. Defaults match the spec.

| Setting | Default | Meaning |
|---|---|---|
| Taste half-life (days) | `90` | How fast older watch events fade when building taste affinities. |
| Cooldown period (days) | `21` | Length of the post-watch suppression before rediscovery begins. |
| Freshness strength | `1.0` | Multiplier on the cooldown/rediscovery effect. |
| Wildcard % | `2.0` | Share of the library promoted as low-confidence "wildcards" each day. |
| Blend manual ratings as a taste prior | `false` | If on, a manual `rating100` nudges the taste model — a performer's rating nudges their affinity, and a **scene's** rating nudges that scene's base score (read-only). With the rating100 mirror on, originals are read from the backup snapshot to avoid a feedback loop. |
| Also mirror score to rating100 (destructive) | `false` | If on, each entity's score is **also** written to native `rating100` (enables the in-app *Rating, descending* sort). **Overwrites manual ratings** — a backup is auto-created first; revert with **Restore Ratings**. |
| Exclusion tag name | `[Restash: Exclude]` | Entities with this tag are dropped from scoring entirely; any existing `restash_*` keys on them are removed. |

Operational knobs (batch size, retry/backoff, the subset-first write cap) are tuned for safe
defaults and set programmatically rather than through the UI.

!!! warning "rating100 mirror is destructive"
    With **Also mirror score to rating100** on, every scored entity's native `rating100` is
    overwritten with its Restash score. Before the first mirror write, Restash **auto-creates a
    backup** (`restash_ratings_backup.json` in the plugin folder); you can also snapshot manually with
    the **Backup Ratings** task (which keeps timestamped history). Run **Restore Ratings** to revert
    the library to the exact backup snapshot. Turning the toggle back off stops future mirror writes
    but does not auto-revert.

!!! note "Dry run"
    A "dry run" is simply the **Dry Run Report** task — there's no separate toggle.
