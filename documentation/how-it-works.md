# How scoring works

A plain-English tour of how the score is built. The maths stays exactly as implemented; this is just
the narration.

- **Events.** Each play counts ~1× how completely it was watched (floored so a quick sample still
  counts a little); an "o" counts ~4× a full play — it's the strongest positive signal. A play that
  was abandoned early **and** barely watched gets a small penalty.
  *(0.1.0 detail D11: abandonment requires low completion too, because Stash resets a scene's resume
  position to 0 once it's finished — so resume-position alone would wrongly punish fully-watched
  scenes.)*
- **Taste model.** Every tag/performer/studio accumulates time-decayed event value, normalised so
  merely-common tags don't win by ubiquity, then standardised and squashed into roughly −1…+1. A
  favourited performer gets a fixed bump.
- **Scene base.** A blend of top performer affinities, rarer-tag-weighted tag affinities, studio
  affinity, and a quality prior (resolution, a learned duration "sweet spot", marker density,
  organised flag). Scenes you *have* watched blend in their own direct evidence, weighted by how much
  history they have.
- **Freshness.** From days since you last engaged: buried for the first couple of days, recovering
  across the cooldown window, then a rediscovery bonus that peaks months out. Never-watched scenes
  instead get a **novelty** boost that fades over their first month.
  *(0.1.0 detail D13: a scene's own evidence decays on a slower 365-day clock than the 90-day taste
  clock, so genuine old favourites actually climb back instead of fading.)*
- **Satiation.** A category over ~25% of the last week's activity is damped (down to a floor), so a
  binge quietly rotates the feed toward everything else and recovers within days once you stop.
- **Serendipity.** A tiny deterministic daily jitter breaks ties (stable all day, different
  tomorrow), and a few low-confidence "wildcards" are promoted into the upper band to keep the model
  learning.
- **Normalise.** Rank everything and map to 0–100 by percentile (ties share the average rank, which
  is what makes two same-day runs reproducible).
- **Performers** are scored from their best (shrinkage-adjusted) scenes, their own affinity, their
  freshness, their unwatched-but-loved supply, and newcomer novelty; favourites are floored at the
  60th percentile. *(0.1.0 detail D12: a performer's best-scenes term is shrunk toward the population
  mean by how many scored scenes they have, so a one-scene ensemble cast can't all sit at the
  ceiling.)*

## Manual ratings as a prior

When **Blend manual ratings as a taste prior** is on, a manual `rating100` feeds the model:
a performer's rating nudges their affinity, and a **scene's** rating is added to that scene's
pre-freshness base as `(rating − 50) / 50 × scene_rating_weight` (default `0.5`). Because it blends
into the base, freshness and cooldown still apply on top, and Quick Refresh inherits it from the
cached base.

If you also enable the **rating100 mirror**, Restash overwrites `rating100` with its own score — so
to avoid feeding its own output back in as a "manual" rating, the prior is read from the pre-mirror
**backup snapshot** instead of the live field. (Manual ratings you set *after* mirroring won't be
picked up until you Restore, re-rate, and Backup again.)

## A note on determinism

The date-seeded parts (jitter, wildcards) are identical all day, but the freshness/novelty terms
move with the real clock. So an immediate re-run rewrites only the entities whose **integer**
percentile actually shifted — most scenes are skipped, though performers churn more: their scores
ride a global percentile re-rank, so a microscopic shift flips many across rounding boundaries.
**Quick Refresh** behaves the same way and shares the same skip-unchanged write path, so a scheduled
daily run stays cheap.
