# Troubleshooting

- **"This Stash build lacks scene custom_fields…" on startup.** Your Stash predates scene custom
  fields. Upgrade to a recent stable build (v0.30+) and re-run.
- **`ModuleNotFoundError: stashapi`.** `stashapp-tools` isn't installed for the Python Stash invokes.
  Install it there (see [Docker / Alpine notes](install.md#docker-alpine-notes)).
- **`python: not found` (Docker/Alpine).** The image exposes `python3` only — install a `python` shim
  or change `exec:` in `restash.yml` to `python3`.
- **GraphQL content-type / transport errors after a Stash upgrade.** v0.29 changed the GraphQL
  response content-type; this is handled by `stashapp-tools`, so keep it updated.
- **A task seems to do nothing.** The plugin is task-only and registers no update hooks (deliberate,
  to avoid self-triggering loops). Check **Settings → Logs**; `Recompute All` logs how many entities
  it wrote/skipped, and reports a non-zero exit if the server rejected any update.
- **Scores didn't change on a re-run.** Expected — `Recompute All` skips entities whose score is
  unchanged. See the [determinism note](how-it-works.md#a-note-on-determinism).
- **Other plugins ran unexpectedly after a recompute.** Expected — each entity Restash writes is a
  Stash update, which fires Stash's update hooks, so any other plugin on a scene/performer update hook
  runs too (once per written entity). This is most noticeable on the first full recompute of a large
  library. See [Writing triggers other plugins' update hooks](usage.md#update-hooks).
