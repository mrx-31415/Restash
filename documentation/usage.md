# Usage

Run tasks from **Settings → Tasks** in the Stash UI. Recommended first run: **Dry Run Report**,
eyeball the breakdown, then **Recompute All**.

| Task | Mode | What it does |
|---|---|---|
| **Dry Run Report** | `dry` | Reads + scores everything, **writes nothing**, logs the top-30 scenes and performers with every term itemised. Safe to run anytime. |
| **Recompute All** | `full` | Reads, rebuilds the taste model, scores, and **writes** `restash_*` to scenes + performers. Skips entities whose score is unchanged. |
| **Quick Refresh** | `refresh` | Fast daily re-score from the cached taste model (written by `Recompute All`): re-applies freshness, novelty, jitter, and wildcards **without** rebuilding affinities or reading watch histories. Self-heals to a full recompute if the cache is missing or stale. See [Scheduling](scheduling.md). |
| **Clear Restash Data** | `clear` | Removes the `restash_*` keys from every entity. Other custom fields and `rating100` are left untouched. |

!!! note "Non-destructive by design"
    Writes use the **partial** form of `CustomFieldsInput` (merge), so your own custom fields
    survive; `Clear` uses the **remove** form. The plugin **never writes `rating100`**, and it
    registers no update hooks (so it can't trigger itself).

<a id="update-hooks"></a>

!!! warning "Writing triggers other plugins' update hooks"
    Restash registers no hooks of its own, but **every entity it writes is a Scene/Performer update
    in Stash, which fires Stash's update hooks** — so any *other* plugin you have installed that runs
    on a scene or performer update hook will be triggered, **once per written entity**.

    On a large library this matters: `Recompute All`'s first run writes everything in scope (and
    `Clear Restash Data` writes every entity too), so thousands of writes can set off thousands of
    hook invocations in those other plugins — potentially slow, and in some setups cascading. After
    the first full run, `Recompute All` and `Quick Refresh` skip unchanged entities, so steady-state
    daily refreshes write — and therefore trigger — far fewer.

    If that's a concern, **run `Dry Run Report` first** (it writes nothing, so it fires no hooks), and
    consider temporarily disabling other update-hook plugins for the initial full recompute.

## The taste-model cache

`Recompute All` writes a `restash_state.json` file next to the plugin (in the `restash/` folder)
holding the affinity model and each scene's pre-freshness base. **Quick Refresh** reads it to skip
the expensive affinity rebuild and history read. It's a pure speed cache: the authoritative scores
live in `custom_fields`, and the file is fully regenerable — delete it (or change a scoring setting)
and the next Quick Refresh self-heals by running a full recompute. It's local-only and never
committed to git.
