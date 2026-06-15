# Restash

A freshness-scoring plugin for [Stash](https://github.com/stashapp/stash). Restash reads the
behavioural log Stash already keeps for every Scene and Performer — plays, o-history (with
timestamps), how completely each scene was watched, when it entered the library — and turns it
into a personalised **0–100 "freshness" score**. The score answers *"what do I want to see right
now?"* and changes over time.

The score is written **only** into each entity's `custom_fields` (keys prefixed `restash_`). The
native `rating100` star rating is **never touched by default** — an optional, reversible mirror
exists if you want it (see [Mirroring to rating100](usage.md#mirroring-to-rating100)).

!!! info "Status — 0.3.0"
    The scoring engine, the write path (`Recompute All`, `Clear Restash Data`), and
    `Quick Refresh` (a fast daily re-score from a cached taste model) are complete and validated
    end-to-end against a real ~5,900-scene library. The optional `rating100` mirror (with
    **Backup/Restore Ratings**) and the manual-rating taste prior are now available.

## What it does

Stash passively records a rich behavioural log but nobody hand-curates ratings at library scale —
yet the watch history *is* the rating, it just needs decoding. Restash builds the score from four
ideas:

1. **Taste, learned not declared.** It builds affinity weights for your tags, performers, and
   studios from time-decayed o-history and play-completion. A scene scores well if its
   *ingredients* score well — even if you've never played it.
2. **Freshness: cooldown then rediscovery.** Something you just watched is buried; a long-unwatched
   favourite slowly climbs back above baseline. The curve dips right after a watch, recovers over a
   few weeks, and peaks months later.
3. **Satiation.** If the last week's activity is dominated by one tag or performer, that whole
   category is temporarily damped so the feed steers toward variety instead of feeding a binge back
   to you.
4. **Controlled serendipity.** A deterministic daily jitter reshuffles near-ties so the top of the
   grid looks different each day, plus a small "wildcard" slot that surfaces low-confidence items to
   keep the model learning.

Final scores are **percentile-ranked** across the library and mapped to 0–100, so the full range is
always used and a descending sort produces a smooth feed rather than a wall of 50s.

## What gets written

Restash partial-merges four keys into each in-scope entity's `custom_fields` (your other custom
fields are preserved):

| Key | Type | Meaning |
|---|---|---|
| `restash_score` | int 1–100 | the headline percentile-ranked score |
| `restash_raw` | float | the pre-percentile raw score (for debugging/tuning) |
| `restash_components` | JSON string | itemised terms (base, fresh, novelty, jitter, …) |
| `restash_updated` | UTC ISO-8601 | when this entity was last scored |

`restash_score` is floored at 1, so an API consumer can treat absent/0 as "not scored".

`rating100` (native rating) is written **only** when the optional *Also mirror score to rating100*
setting is enabled — off by default, and reversible via **Backup/Restore Ratings**.

## Where to next

- New here? Start with **[Installation](install.md)**, then run a **[Dry Run Report](usage.md)**.
- Want to understand the maths? See **[How scoring works](how-it-works.md)**.
- Automating a daily re-score? See **[Scheduling](scheduling.md)**.

## Requirements

- **Stash** with scene + performer `custom_fields` support. Performer custom fields landed in v0.28;
  scene custom fields and `CustomFieldsInput.remove` are in recent stable (v0.30+). Restash probes
  the schema on startup and fails with a clear message if your build is too old. Developed and
  validated against **Stash v0.31.1**.
- **Python 3.11+** available to the Stash host (this is what runs the plugin).
- **[`stashapp-tools`](https://pypi.org/project/stashapp-tools/)** (`stashapi`) ≥ 0.2.58, installed
  for that same Python.

## License

[MIT](https://github.com/Espionage9248/Restash/blob/main/LICENSE) © 2026 Espionage9248.
