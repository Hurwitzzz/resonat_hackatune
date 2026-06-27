# `backend/profile` — User-defined Taste Memory

The **user-profile** module for Cochlea. It turns a listener's feedback
(like / dislike / skip / free-text note) into an **explainable, per-user taste
memory** stored as Markdown, and serves it to the rest of the backend.

Maps to PRD §7 (the two memory consumers) and the `/feedback` + `/your-sound`
endpoints. Memory is built from **likes** (positive signal); dislike/skip push
affinities down; notes are stored verbatim. Every preference traces back to real
Cyanite tags — **no opaque latent vector**, so it stays explainable.

---

## Structure

```
backend/profile/
  api.py           FastAPI routes (router + standalone app)
  mdmemory.py      core: record_feedback() + markdown storage + read views
  cyanite_tags.py  minimal Cyanite tagging client (disk cache + rate limit)
  tags.py          normalize raw model outputs -> flat tags
  data.py          data-pack id mapping + audio url (for demo/seed/eval)
  config.py        env / paths (reads repo-root .env)
  test_feedback.py simulated feedback stream (runnable demo)
  memories/        per-user .md memory files (runtime; git-ignored)
  .cache/          cached Cyanite tags (runtime; git-ignored)
```

## Run

```bash
# from the repo root, with the `hackatune` conda env
uvicorn backend.profile.api:app --reload --port 8001   # docs at /docs

# or run the simulated feedback demo
python -m backend.profile.test_feedback
```

Needs `CYANITE_API_KEY` in the repo-root `.env`. With no key it runs in **MOCK**
mode (deterministic fake tags) so the module is testable offline.

---

## The one interface

```python
from backend.profile import mdmemory

mdmemory.record_feedback(
    user_id, track_id, verdict,      # verdict: like | dislike | skip | play | note
    prompt=None,                     # the search/Query the track came from
    note=None,                       # free-text "other info" from the user
    track_tags=None,                 # optional; fetched from Cyanite (cached) if absent
) -> summary_dict
```

Read views:

```python
mdmemory.summary(user_id)               # headline + structured prefs (for /your-sound)
mdmemory.seed_pool(user_id, prompt=...) # liked track ids -> similarById seeds
mdmemory.prompt_injection(user_id)      # taste block to prepend to the /intent system prompt
```

## HTTP endpoints

| Method | Path | Purpose | Consumer |
|---|---|---|---|
| POST | `/feedback` | record one event → updated summary | `/feedback` loop |
| POST | `/feedback/batch` | record a list of events | replay / batch |
| GET | `/your-sound/{user_id}` | memory summary | `GET /your-sound` |
| GET | `/profile/{user_id}/seeds?prompt=&limit=` | liked-track seed pool | search side |
| GET | `/profile/{user_id}/injection` | system-prompt taste block | `/intent` |
| GET | `/profile/{user_id}/markdown` | raw markdown memory | demo |
| GET | `/health` | `{ok, mock}` | — |

## Integrate (two ways)

```python
# 1) mount the router in the main app (preferred)
from backend.profile.api import router as profile_router
main_app.include_router(profile_router)

# 2) or call the functions directly from your own /feedback handler
from backend.profile import mdmemory
mdmemory.record_feedback(uid, tid, "like", prompt=prompt)   # persist the like
seeds = mdmemory.seed_pool(uid, prompt=prompt)              # for similarById
inject = mdmemory.prompt_injection(uid)                     # for /intent
```

> ⚠️ In the PRD, `POST /feedback` also does neighbourhood **pruning/backfill/rerank**
> (search side, owned by another teammate). This module only persists memory.
> Pick one: have the main `/feedback` call `record_feedback()` internally, or use
> integration (2) — so two owners don't both register `POST /feedback`.

## Storage format

One Markdown file per user (`memories/<user_id>.md`): a human-readable taste
profile (likes %, avoids, scenario memory, notes, recent feedback) plus a fenced
` ```json ` machine-state block at the bottom that we parse on load. Human-facing
and machine-readable in one file.

> Storage is Markdown, but the **function/HTTP contract matches the PRD** — the
> storage backend (md vs the PRD's SQLite) is internal and swappable without
> changing how `/feedback`, `/intent`, or `/your-sound` integrate.

## Notes

- **Quota is shared across all teams** → tags are fetched once and cached in
  `.cache/`; the client stays under ~110 tagging calls/min.
- Per the challenge license, **Cyanite model outputs (`.cache/`) and runtime
  memories are git-ignored** — do not commit them.
- Optional LLM phrasing for `/your-sound` activates only if `ANTHROPIC_API_KEY`
  is set; it rephrases, never invents preferences.
