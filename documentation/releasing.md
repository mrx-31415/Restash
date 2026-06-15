# Releasing

`restash.yml`'s `version:` is what the Stash UI shows — it is **not** derived from the git tag, so it
must be bumped in the same commit as any release tag. `scripts/check_version.py <tag>` enforces this
(exit 1 on mismatch), and CI runs it automatically on tag pushes:

```bash
python scripts/check_version.py v0.2.0   # OK when restash.yml says 0.2.0
```

## What deploys, and when

Every push to `main` runs the Pages workflow, which:

1. Builds the documentation site with `mkdocs build`.
2. Runs `scripts/build_source.sh` to regenerate the plugin source manifest
   (`index.yml` + `restash.zip`) on top of the built docs.
3. Publishes everything to GitHub Pages.

So a version bump to `restash.yml` on `main` updates the in-app plugin source automatically — no
separate publish step. See [Publishing the site](publishing.md) for the mechanics.
