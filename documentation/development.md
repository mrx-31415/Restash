# Development

The repo root is a small Python project; the installable plugin is the `restash/` folder.

```bash
python -m venv .venv && . .venv/bin/activate
pip install stashapp-tools pytest
pytest                      # 120+ offline unit tests, no Stash needed
```

`restash/tools/run_local.py` runs a task locally by feeding `restash.py` the same stdin JSON Stash
would send.

!!! danger "Connects to a live Stash"
    `run_local.py` talks to a real Stash server — only run it intentionally.

```bash
# Dry run against a live server (reads only):
python restash/tools/run_local.py --url http://HOST:9999 --mode dry

# Subset-first write gate — write to only the first N entities:
python restash/tools/run_local.py --url http://HOST:9999 --mode full --limit 5

# Targeted write — write to only specific scene IDs (e.g. to verify non-destructive
# merging against scenes you know already have custom fields):
python restash/tools/run_local.py --url http://HOST:9999 --mode full --ids 8137,8138,8139
```

Pass `--api-key KEY` if your Stash has authentication enabled.

## Working on the docs

The documentation site is MkDocs Material. To preview it locally:

```bash
pip install -r requirements-docs.txt
mkdocs serve            # live-reload preview at http://127.0.0.1:8000
```

Pages live in `documentation/`; the nav and theme are configured in `mkdocs.yml`. See
[Publishing the site](publishing.md) for how docs and the plugin source are deployed together.
