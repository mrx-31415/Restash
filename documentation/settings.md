# Settings

Exposed under **Settings → Plugins → Restash**. Defaults match the spec.

| Setting | Default | Meaning |
|---|---|---|
| Taste half-life (days) | `90` | How fast older watch events fade when building taste affinities. |
| Cooldown period (days) | `21` | Length of the post-watch suppression before rediscovery begins. |
| Freshness strength | `1.0` | Multiplier on the cooldown/rediscovery effect. |
| Wildcard % | `2.0` | Share of the library promoted as low-confidence "wildcards" each day. |
| Blend manual ratings as a taste prior | `false` | If on, a performer's manual `rating100` nudges their affinity (read-only; never written back). |
| Exclusion tag name | `[Restash: Exclude]` | Entities with this tag are dropped from scoring entirely; any existing `restash_*` keys on them are removed. |

Operational knobs (batch size, retry/backoff, the subset-first write cap) are tuned for safe
defaults and set programmatically rather than through the UI.

!!! note "rating100 mirror"
    Restash never writes the native `rating100` rating. An optional mirror (also write the score to
    `rating100`, for native UI sorting) is planned as a separate future release and will add its own
    setting when it lands. A "dry run" is simply the **Dry Run Report** task — there's no separate
    toggle.
