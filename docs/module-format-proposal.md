# FUR module manager: implementation and limits

FUR management is implemented by the System module. The public registry is fixed to `Fear-Selfbot/fear-repository/main/registry.json`; user input is always a validated module ID, never a URL or package specifier.

## Runtime flow

1. `.flist`, `.fins`, `.frem`, and `.fupd` are registered in `modules/system/main.py` and filtered with `filters.me`.
2. Fear reads package metadata from FUR, downloads a ZIP from the configured raw GitHub host and compares its SHA-256 with the registry.
3. It validates ZIP member paths, symlinks, total expanded size, `fear-module.json`, package ID and version. The package is unpacked to a hidden staging directory below `modules/`.
4. Optional dependencies from a hash-pinned `requirements.lock` are installed using the external `uv` executable, into a staging directory below `.data/module-deps/`; hashes are required and wheels only are accepted. The asyncio event loop is not blocked while downloading or installing.
5. Fear swaps the staged files into place, updates `.data/fur-installed.json`, and asks the loader to import/register the modules while the Telegram clients keep running. If activation fails, it restores the previous package files and install record.
6. On removal, package files are first quarantined, then handlers are reloaded; success deletes the quarantine, failure restores it.

The on-disk layout is:

```text
modules/<module-id>/main.py
modules/<module-id>/fear-module.json
modules/<module-id>/requirements.lock  # optional, hash-pinned
.data/module-deps/<module-id>/          # installed wheel contents
.data/fur-installed.json
```

The exact registry and module example are documented in [docs/modules.md](modules.md) and the [FUR repository README](https://github.com/Fear-Selfbot/fear-repository).

## Operational and security limits

- FUR digest verification detects a package that does not match the current registry. Since the same repository publishes both, it is not an independent signature or publisher identity check.
- Module code executes in-process with Fear's OS permissions. It can access Telegram clients and process secrets; permissions in a manifest would not sandbox it.
- Module dependencies have separate install directories but share Python's global import cache. Conflicting library versions, native extensions already loaded, and code with import-time side effects cannot be reliably replaced/unloaded live.
- Dependency installation requires `uv` on PATH. `requirements.lock` must pin exact versions and hashes; only binary wheels are accepted to avoid building source distributions during bot operation.
- Runtime install does not restart Telegram clients or the Python process. If a module depends on replacing an already imported dependency, restart the Python process manually after update/removal.
- The package format currently requires `main.py` and `fear-module.json` at the ZIP root or one top-level directory. The manifest entrypoint field is informational; current loader entrypoint remains `main.py`.

For mutually untrusted modules or conflicting dependencies, use separate worker processes with a narrow IPC host API. A per-module `--target` directory alone is not dependency isolation.
