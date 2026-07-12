# Usage

Run tasks from **Settings → Tasks** in the Stash UI. Recommended first run: **Dry Run Report**,
eyeball the breakdown, then **Recompute All**.

## Fresh scenes page

Open **Fresh** in the main navigation or visit `/restash/freshness` to browse scenes ordered by the
canonical `restash_score` custom field. The page does not read or change `rating100`.

Search, set a freshness threshold, switch between grid, list, and wall views, adjust card size,
or change the page size. The default
threshold is 95 and can be changed under **Settings → Plugins → Restash**. View state is preserved
in the `search`, `min`, `op`, `page`, and `pageSize` URL parameters.

Use **Quick Refresh** or **Recompute All** to queue those Restash tasks directly from the page.

Restash loads matching scores in batches, sorts them in the browser, and fetches native card data
only for the current page. Bulk operations are not available in this first version.

| Task | Mode | What it does |
|---|---|---|
| **Dry Run Report** | `dry` | Reads + scores everything, **writes nothing**, logs the top-30 scenes and performers with every term itemised. Safe to run anytime. |
| **Recompute All** | `full` | Reads, rebuilds the taste model, scores, and **writes** `restash_*` to scenes + performers. Skips entities whose score is unchanged. |
| **Quick Refresh** | `refresh` | Fast daily re-score from the cached taste model (written by `Recompute All`): re-applies freshness, novelty, jitter, and wildcards **without** rebuilding affinities or reading watch histories. Self-heals to a full recompute if the cache is missing or stale. See [Scheduling](scheduling.md). |
| **Clear Restash Data** | `clear` | Removes the `restash_*` keys from every entity. Other custom fields and `rating100` are left untouched. |
| **Backup Ratings** | `backup-ratings` | Snapshots every scene/performer's current native `rating100` to `restash_ratings_backup.json` in the plugin folder. Rotates any existing backup to a timestamped copy. Run before enabling the mirror. |
| **Restore Ratings** | `restore-ratings` | Writes the backed-up `rating100` values back, reverting the library to the exact backup snapshot (restores originals **and** clears mirror-applied ratings). |

!!! note "Non-destructive by design"
    Writes use the **partial** form of `CustomFieldsInput` (merge), so your own custom fields
    survive; `Clear` uses the **remove** form. By default the plugin **never writes `rating100`**
    (only the optional, reversible mirror does — see [Mirroring to rating100](#mirroring-to-rating100)),
    and it registers no update hooks (so it can't trigger itself).

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

## Mirroring to rating100

By default Restash never touches the native `rating100` star rating. If you want the in-app
*Rating, descending* sort to follow your Restash score, enable **Also mirror score to rating100** in
Settings. The workflow:

1. (Optional) Run **Backup Ratings** for an explicit snapshot — the first mirror write auto-creates
   one anyway.
2. Enable the toggle and run **Recompute All** (or **Quick Refresh**). Each written entity now gets
   `rating100 = restash_score`.
3. To undo, run **Restore Ratings** — it reverts `rating100` to the backup snapshot exactly.

!!! tip "Also enable *Blend manual ratings as a taste prior*"
    Once the mirror overwrites your live `rating100`, that field is Restash's own output — so to keep
    your **manual** ratings influencing the model, turn on **Blend manual ratings as a taste prior**
    too. With both on, the prior is read from the pre-mirror **backup snapshot** (not the overwritten
    live field). If you leave it off, your manual ratings stop feeding the model the moment you mirror.

!!! note
    Restore reverts to the **backup snapshot**: any native ratings you set *after* the backup are
    discarded. When the mirror is on, an entity is also re-written if its score is unchanged but its
    `rating100` doesn't match yet (so flipping the toggle on mirrors the whole library on the next run).

## The taste-model cache

`Recompute All` writes a `restash_state.json` file next to the plugin (in the `restash/` folder)
holding the affinity model and each scene's pre-freshness base. **Quick Refresh** reads it to skip
the expensive affinity rebuild and history read. It's a pure speed cache: the authoritative scores
live in `custom_fields`, and the file is fully regenerable — delete it (or change a scoring setting)
and the next Quick Refresh self-heals by running a full recompute. It's local-only and never
committed to git.
