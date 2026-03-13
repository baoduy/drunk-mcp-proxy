# Legacy Documentation Archive

This folder previously contained pre-restructure documentation snapshots.

## Current policy

- Stale legacy files were removed to keep docs clean and reduce confusion.
- Historical content remains available through Git history.
- New and maintained docs live under module-scoped paths:
  - `docs/drunk_ai_proxy/`
  - `docs/drunk_ai_client/`

## Where to look now

- Proxy docs index: `docs/drunk_ai_proxy/INDEX.md`
- Client docs index: `docs/drunk_ai_client/INDEX.md`
- Global docs router: `docs/README.md`

## Recovering removed legacy docs

Use Git history if you need old references:

- `git log -- docs/drunk_ai_proxy/legacy/`
- `git show <commit>:docs/drunk_ai_proxy/legacy/<file>.md`
