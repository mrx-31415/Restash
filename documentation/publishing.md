# Publishing the site

Restash serves **two things from one GitHub Pages site**, and they must not collide:

| URL | Served file | Audience |
|---|---|---|
| `https://espionage9248.github.io/Restash/` | `index.html` (MkDocs) | humans reading docs |
| `https://espionage9248.github.io/Restash/index.yml` | `index.yml` (+ `restash.zip`) | the Stash plugin-source installer |

These don't conflict: the docs landing page is `index.**html**`, the plugin manifest is
`index.**yml**` — different files, both at the site root.

!!! danger "Don't break the plugin-source URL"
    Users have already added `…/Restash/index.yml` as a Stash plugin source. `index.yml` and
    `restash.zip` must stay reachable at the **site root** with those exact names. Any change to the
    publish pipeline has to preserve that.

## How the pipeline works

Pages is deployed by GitHub Actions (artifact upload, not a branch) from
[`.github/workflows/pages.yml`](https://github.com/Espionage9248/Restash/blob/main/.github/workflows/pages.yml).
On every push to `main` it:

1. **`mkdocs build`** — writes the static docs site into `_site/` (a clean build that wipes the dir).
2. **`scripts/build_source.sh`** — zips `restash/` into `_site/restash.zip` and writes
   `_site/index.yml`, *layering* the plugin source on top of the docs output.
3. **Upload + deploy** — `_site/` is uploaded as the Pages artifact and published.

Order matters: MkDocs runs **first** because it clears `_site/`; the manifest step runs **second** and
only adds files, so it survives. `build_source.sh` therefore does **not** `rm -rf _site` — it relies on
MkDocs having created (and cleaned) the directory first.

## Source layout

- `mkdocs.yml` — site config. `docs_dir: documentation`, `site_dir: _site`.
- `documentation/` — the Markdown pages (tracked in git).
- `requirements-docs.txt` — the MkDocs Material toolchain (docs-only; not a plugin runtime dep).
- `_site/` — build output; git-ignored.

!!! note "Why `documentation/` and not `docs/`?"
    This repo's `docs/` is git-ignored and holds internal plans/specs, so it can't be the published
    source. MkDocs is pointed at `documentation/` via `docs_dir` instead.

## Previewing locally

```bash
pip install -r requirements-docs.txt
mkdocs serve     # http://127.0.0.1:8000, live reload

# Full production build exactly as CI does it:
mkdocs build
bash scripts/build_source.sh
# now _site/ contains the docs HTML + index.yml + restash.zip
```
