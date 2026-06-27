# Sounds Like You

**Cyanite challenge for HACKATUNE 2026 (Munich Music Labs).**

Build a music discovery experience on the Cyanite API that recommends tracks based on
how they actually sound, driven by natural language, seed tracks, and a listener's
taste. Every recommendation should be
explainable, so a user can ask "why this track?" and get a clear answer grounded in
Cyanite's audio tags.

Read the full brief in [CHALLENGE.md](CHALLENGE.md).

## What's in this repo

| Path | What it is |
|---|---|
| `CHALLENGE.md` | The challenge: what to build, ideas, and judging criteria |
| `CHALLENGE_AGREEMENT.md` | Terms for participating in the Cyanite challenge (accepted at registration) |
| `data/` | The data pack (taste profiles + track display info) |
| `notebooks/` | Python starter notebook: model outputs + search (text, similarity, multi-track) with audio |
| `guides/` | Cyanite API guides (endpoint PDFs) + model outputs and tag-vocabulary reference |
| `.env.sample` | Template for your Cyanite API key |
| `LICENSE` | MIT, for the code and docs in this repo |
| `DATA_LICENSE.md` | Terms for the data pack (Creative Commons music, pseudonymized profiles) |

## Getting started

1. Clone this repo.
2. Copy the env template and add your Cyanite API key (handed out by the organizers at the event):
   ```bash
   cp .env.sample .env
   # then edit .env and set CYANITE_API_KEY
   ```
3. Read [CHALLENGE.md](CHALLENGE.md), then open the starter notebook [`notebooks/cyanite_model_outputs.ipynb`](notebooks/cyanite_model_outputs.ipynb); skim the [tag vocabularies](guides/tag_vocabularies.md).
4. Explore `data/` (see below) and start querying the Cyanite API by track ID or text prompt.

For the Cyanite API, use the starter notebook
[`notebooks/cyanite_model_outputs.ipynb`](notebooks/cyanite_model_outputs.ipynb) (covers all four
endpoints) and the guides in [`guides/`](guides/) (endpoint PDFs, model outputs, tag vocabularies).

## The data pack

Everything is restricted to a catalog of tracks that are indexed in Cyanite, so any track ID you see
is queryable.

| File | Columns | Notes |
|---|---|---|
| `data/users.csv` | `user_id, liked_track_ids` | Pseudonymized user profiles (numeric IDs only). `liked_track_ids` is a space-separated list of Jamendo track IDs, e.g. `df["liked_track_ids"].str.split()` |
| `data/tracks.csv` | `track_id, cyanite_id, name, artist_name, duration` | Display info for the tracks referenced by the user profiles |

**Two id spaces:** `track_id` is the **Jamendo** id (used for the audio URL and for joining
`users.csv`); `cyanite_id` (`libtr_...`) is the id you pass to the **Cyanite API**. Join
`users.csv` to `tracks.csv` on `track_id` to get the `cyanite_id` for a user's liked tracks.
Every track in the pack has a `cyanite_id`.

Use the user profiles as seeds for content-based taste profiles (the sound of what a
user likes), not as collaborative-filtering / co-listening signals. See
[DATA_LICENSE.md](DATA_LICENSE.md) for music attribution and data-use terms.

### Audio

Audio is available as public MP3 for any track at a
deterministic URL, so you can fetch audio for any catalog or search-result track ID:

```js
`https://prod-1.storage.jamendo.com/download/track/${trackId}/mp32/`
```

e.g., for track ID `391816`:
```
https://prod-1.storage.jamendo.com/download/track/391816/mp32/
```

Replace `<track_id>` with the numeric ID (no API key needed). A small number of tracks
that disallow download on Jamendo may not resolve.

## The Cyanite API (four endpoints)

Base URL `https://rest-api.cyanite.ai/v1`, auth header `x-api-key: <your key>`.
Search for catalog tracks using track ids, prompts, tags, and metadata filters.

- **Find by text prompt**: `POST /private-alpha/library-tracks/search`, body `{"query": "..."}`
- **Find similar (single seed)**: `POST /private-alpha/library-tracks/{id}/similar`
- **Find similar (multi-track, up to 10 seeds)**: `POST /private-alpha/library-tracks/similar`, body `{"tracks": [{"id": "libtr_..."}]}`
- **Model outputs (tags)**: `GET /library-tracks/{id}/models?model=MoodSimpleV2&model=MainGenreV2&...`

The three search endpoints return `{"items": [{"track": {...}, "score": 0..1}], "pageInfo": {...}}`
ordered by relevance/similarity; fetch a result's tags via the model-outputs endpoint to explain it.

**Metadata filters.** All search modes accept an optional `metadataFilter`, applied before
ranking. It is a MongoDB-style filter keyed by the model-output field in **dot notation**,
`"<ModelVersion>.<field>"`. Operators: `$gte $lte $gt $lt $eq $ne $in $nin $exists`, plus the
logical `$and` / `$or`.

```json
{ "BpmV2.tag": { "$gte": 120, "$lte": 140 } }
{ "TempoV1.tag": { "$eq": "fast" } }
{ "MainGenreV2.tags": { "$in": ["rock", "pop"] } }
{ "MoodSimpleV2.scores.energetic": { "$gte": 0.5 } }
{ "$and": [ { "BpmV2.tag": { "$gte": 100 } }, { "InstrumentsV2.tags": { "$in": ["piano"] } } ] }
```

Filter keys follow the model-output fields: `.tag` (single value), `.tags` (array, use `$in` /
`$nin`), or `.scores.<tag>` (numeric per-tag score). See [model outputs](guides/model_outputs.md)
for the fields and [tag vocabularies](guides/tag_vocabularies.md) for valid tag values.

See [CHALLENGE.md](CHALLENGE.md) for the loop and the
[starter notebook](notebooks/cyanite_model_outputs.ipynb) for runnable examples.

## API usage and limits

The API key is shared for the event and usage limits are **pooled across all teams**, so
please cache results and fetch only what you use, so everyone has capacity for the full
36 hours. Each action has a per-minute rate limit and an overall event quota:

| Action | Rate limit (per minute) | Event quota (total) |
|---|---|---|
| Prompt search | 100 / min | 15,000 |
| Similarity search | 100 / min | 15,000 |
| Tagging / model outputs (per track) | 180 / min | 50,000 |

- Exceeding a rate limit returns a rate-limit error; wait a few seconds and retry.
- Exceeding an event quota stops further calls for that action for the rest of the event.
- **Cache tags locally and fetch each track once.** A search returns up to 500 IDs; only tag the tracks your app actually surfaces, and avoid bulk-tagging the catalog.
- Per the [Challenge Agreement](CHALLENGE_AGREEMENT.md), data and model outputs are for event use only: do not publish or redistribute them, and delete them after the event.

## Terms and licenses

- Participating in the Cyanite challenge means accepting [CHALLENGE_AGREEMENT.md](CHALLENGE_AGREEMENT.md). Acceptance is recorded by Munich Music Labs at registration; the copy here is the reference text.
- Code and docs: MIT ([LICENSE](LICENSE)). Data pack: see [DATA_LICENSE.md](DATA_LICENSE.md).
