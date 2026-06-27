# Sounds Like You
### Taste-driven, explainable music recommendation (Munich Music Labs × Cyanite)

> How can people discover music through how it actually sounds, by taste, by mood, by
> "something like this but…", in ways they can understand?

Build a music discovery / recommendation experience on the Cyanite API, grounded in audio (how a track sounds).

---

## The challenge

Most discovery still runs on keyword search, rigid metadata filters, or collaborative
filtering. All of them miss the most direct signal: what the music actually sounds like.
Build discovery that listens.

You have a catalog of ~357,000 tracks already analyzed and indexed by Cyanite's audio AI.
Recommendations should be content/audio-based, driven by mood, instrumentation, energy,
character, and similarity in sound;
and reachable through natural language, seed tracks,
and a listener's taste (taste = the sound of what they like).
And they should be explainable.

### Cross-cutting requirement: Explainability

Let a user ask "why this track?" and get a convincing answer grounded in the audio
analysis: Cyanite's tags/scores, the auto-description, or the prompt/filters you inferred, how the results relate to the given search reference.

---

## Cyanite API workflow

The core loop:
```
search (prompt / seed id(s) [+ metadataFilter])  ->  ranked {track, score}
   -> fetch model outputs per track id  ->  rank / explain / display
```

Four endpoints (base URL `https://rest-api.cyanite.ai/v1`, auth header `x-api-key`):

1. **Search** returns a ranked list of results, each `{track, score}` where `score` is a
   relevance/similarity value in 0 to 1. Three ways to search:
   - **Find by text prompt**: natural language to matching tracks (`POST /private-alpha/library-tracks/search`).
   - **Find similar (single seed)**: a track to acoustically similar tracks (`POST /private-alpha/library-tracks/{id}/similar`).
   - **Find similar (multi-track, up to 10 seeds)**: similar to the mean of several tracks, e.g. a user's likes (`POST /private-alpha/library-tracks/similar`).
   - All three accept an optional **`metadataFilter`** to restrict candidates before ranking (see below).

2. **Model outputs (tagging)**: search returns track ids/titles, not the analysis. To explain
   or re-rank a result, fetch its tags from `GET /library-tracks/{id}/models?model=...`.

> No raw embeddings/vectors are exposed. Build taste/personalization on track ids, prompts,
> tags, and metadata filters.

**Metadata filters.** Both search modes accept an optional `metadataFilter` to keep only tracks
matching structured criteria, applied before ranking. It is a MongoDB-style filter keyed by the
model-output field in **dot notation**, `"<ModelVersion>.<field>"`, where the field is `.tag`
(single value), `.tags` (array; use `$in` / `$nin`), or `.scores.<tag>` (numeric per-tag score).
Operators: `$gte $lte $gt $lt $eq $ne $in $nin $exists`, plus the logical `$and` / `$or`.

```json
{ "BpmV2.tag": { "$gte": 120, "$lte": 140 } }
{ "MainGenreV2.tags": { "$in": ["rock", "pop"] } }
{ "MoodSimpleV2.scores.energetic": { "$gte": 0.5 } }
{ "$and": [ { "TempoV1.tag": { "$eq": "fast" } }, { "InstrumentsV2.tags": { "$in": ["piano"] } } ] }
```

Filter keys follow the model outputs (see guides/model_outputs.md); valid tag values are in
guides/tag_vocabularies.md.

---

## Cyanite tagging: model outputs

Independent per-track outputs (audio analysis). Most taxonomy outputs include per-tag
scores (0 to 1) and time-segmented values, which is what lets you explain what drives a
result and where.

| Output | What it tells you |
|---|---|
| Main genre | High-level genre from a fixed taxonomy (23 genres), with scores |
| Subgenre | Finer genre within the detected main genre (can be null) |
| Free genre | Open-vocabulary genre tags (niche genres, no fixed list) |
| Mood (simple) | Compact mood vocabulary (13 moods), with scores |
| Mood (advanced) | Fine-grained mood (~130 moods), with scores |
| Instruments | Which instruments are present (47), presence level, and where over time |
| Character | Sonic "personality" (e.g. bold, warm, mysterious, playful, epic) |
| Movement | Rhythmic feel / groove (driving, flowing, pulsing, …) beyond raw BPM |
| BPM | Numeric tempo in beats per minute, with confidence |
| Tempo | Coarse perceived tempo label (slow → fast) |
| Key | Musical key, with confidence |
| Time signature | Meter (e.g. 4/4, 3/4), with confidence |
| Valence / Arousal | Continuous emotion axes, plus energy level, energy change, emotion profile, emotion change |
| Musical era | Estimated production era / year the track sounds like |
| Music-for | Use-case / sync suitability tags (hundreds: film, workout, meditation, gaming, …) |
| Vocals | Vocal presence and gender |
| Vocal style | Detailed characterization of any vocals |
| Voiceover | Spoken-word / talkover detection and dominance |
| Auto-description | A short natural-language description of the track |
| Representative segment | Start/end of the most representative part of the track (great for previews) |
| Augmented keywords | A weighted dictionary of free keyword associations |

Additional information on the vocabularies for Cyanite's tags is in [docs/cyanite_tag_vocabularies.md](docs/cyanite_tag_vocabularies.md).

---

## What we provide (data pack)

- Catalog: ~357k tracks sourced from [Jamendo](https://www.jamendo.com/) are indexed and queryable; any track ID returned by the API is in the catalog.
- Audio: a public MP3 is available for any track at a deterministic URL (see the repo README), so you can get audio without any API or extra file.
- Track display info: `track_id, name, artist, duration` for referenced tracks.
- User profiles: real users with their liked tracks (use as seeds for content-based
  taste profiles, not as co-listening signals). Each profile's likes span multiple artists,
  so they capture a genuine taste rather than a single album.<br> Good seeds for taste profiling and offline evaluation (e.g. hold out some of a user's likes
and try to recover them).

(If needed, the Jamendo public API is available for extra live data)

---

## Project ideas

Pick one, combine, or invent your own. Make Cyanite audio-based search central and keep
it explainable.

1. Search as a conversation (steerable discovery).
   Users describe a vibe in natural language and steer: "more energetic… now cinematic…
   add piano… less dark." An LLM translates the dialogue into Cyanite prompt queries +
   tag filters along tag axes (mood, energy, instruments, tempo). Surface the inferred
   prompt/filters each turn and justify each result from its tags.

2. Taste-driven personalized discovery ("Sounds Like You").
   Turn a user's liked tracks into a taste profile from the sound of what they like:
   aggregate their Cyanite tags and/or use their tracks as seeds for search,
   then recommend a personalized stream. Rank and explain each pick by which facet of the taste it
   matches, and let the user steer ("more like this", "less of that").

3. Personalized, steerable radio / continuation.
   From a user's likes (or a few seed tracks they pick), generate an ongoing recommendation
   queue via similar-by-ID re-ranked for tag coherence, with optional prompt nudges
   ("keep the mood but more orchestral"). Explain each next track via shared tags and
   let users accept/reject to refine the direction.

4. Explainable similarity.
   Seed track → similar-by-ID; for each neighbor, explain the match by comparing tag
   profiles (which moods/genres/instruments/tempo align). Use the representative segment
   for instant previews and the auto-description for narration. (Optional: use tag
   "distance" to re-rank away from an unwanted attribute.)

5. Collaborative Discovery.
   - Group Playlists: build playlists based on the collective taste of a group of users, e.g. build a focus playlist for a study group.
   - Trade songs with friends: let users share a track combined with a short description of why they like it, and let the recipient explore similar tracks and see how their tastes align.

6. Unexpected Discovery
- Soundtrack for Stories: Let users input a short story or script, and the app generates a playlist that matches the emotional arc of the narrative.
- Gaming Companions: Create dynamic soundtracks for indie games or tabletop RPGs, adapting to in-game events or player mood.

Stretch / bonus
- Cross-modal prompting: map an image, short video, or a written brief into a Cyanite
  prompt query; explain results via the resulting tags.
- Lightweight visualization of the result set (e.g. laid out by mood/energy).
- Real-time interactive UI, voice input.

---

## What to deliver

A working prototype + a short demo and a few sentences on your approach. Clarity of the
interaction concept and a convincing, explainable demo beat feature count.

## Judging criteria

- Interaction concept: a genuinely more intuitive / conversational / multimodal way to explore music.
- Use of Cyanite search + tagging: advanced, meaningful, audio-based use of the API.
- Recommendation quality: are the results actually good?
- Explainability: can the system justify its results convincingly?
- Execution & demo: does it work, and is it compelling?

---

## Resources at a glance

| Resource | What it gives you |
|---|---|
| Cyanite search | Text prompt, similar-by-ID, and multi-track similarity → ranked tracks + relevance score, with optional metadata filters (no raw embeddings) |
| Cyanite tagging | Per-track audio analysis fetched by track ID (genre, mood, instruments, character, BPM/tempo/key, valence/arousal, era, music-for, auto-description, representative segment, …) with scores + segments |
| Catalog | ~357k tracks indexed in Cyanite (query by ID) |
| Audio | Public MP3 per track at a deterministic URL, no API needed (see README) |
| Data pack | Real user profiles + their liked tracks (CSV) as content-based taste seeds |
| Jamendo public API | Optional extra live data |
