# Installation

## Via plugin source (recommended)

Add Restash as a Stash plugin source and install it from the UI — no manual file copying, and
updates show up in-app:

1. **Settings → Plugins → Available Plugins → Add Source**, then enter:
    - **Name:** `Restash`
    - **Source URL:** `https://espionage9248.github.io/Restash/index.yml`
    - **Local Path:** `restash` (or any folder name you like)
2. Find **Restash** in the Available Plugins list and click **Install**.
3. Install the runtime dependency for the Python that Stash uses (the source ships the plugin code,
   not its Python deps — standard for Stash plugins):
   ```bash
   pip install stashapp-tools
   ```
4. **Settings → Plugins → Reload Plugins.** Restash and its tasks appear under **Settings → Tasks**.

When a new version is published, Stash shows an update on the source — no reinstall needed.

!!! tip "Switching from a manual install?"
    Restash keeps a local cache (`restash_state.json`) inside its plugin folder. Installing to a new
    folder won't carry that cache over — which is harmless, since your scores already live in Stash's
    `custom_fields`; the next run just does a one-time full recompute to rebuild the cache (Quick
    Refresh self-heals to a full run). To skip even that, copy `restash_state.json` from the old
    plugin folder into the new one after installing. Then remove the old manual copy so you don't run
    two Restash plugins.

## Manual install

1. Copy the **`restash/`** folder from this repo into your Stash plugins directory (e.g.
   `~/.stash/plugins/restash/`), so that `restash.yml` sits at `…/plugins/restash/restash.yml`.
2. Install the dependency for the Python that Stash uses:
   ```bash
   pip install stashapp-tools
   ```
3. In Stash, go to **Settings → Plugins** and click **Reload Plugins**. "Restash" should appear with
   its tasks under **Settings → Tasks**.

## Docker / Alpine notes

- Stash's official Docker image runs the plugin with `python`. Install the dependency inside the
  container for that interpreter, e.g. `docker exec <container> pip install stashapp-tools` (Alpine
  images may need `apk add py3-pip` first, and a build toolchain if a wheel isn't available).
- If your environment only exposes `python3` (not `python`), either install a `python` shim or change
  the `exec:` line in `restash.yml` from `python` to `python3`.
- On externally-managed Python installs you may see a PEP 668 "externally-managed-environment" error
  from `pip`; use the interpreter Stash actually invokes (a venv, or
  `pip install --user`/`--break-system-packages` as appropriate for your setup).
