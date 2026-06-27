# Model Outputs

A **model** is an entity of Cyanite's AI that takes an audio track as input and
produces a specific type of musical information as output (for example: mood
scores, BPM, or a key prediction).

A **model output** is the versioned JSON object returned by one such model.

New to Cyanite? Start with the [Quick Start Guide](/docs/intro) to upload your
first track. Then use the
[Get Models endpoint](/reference/api/get-models-by-track-id) to retrieve model
outputs.

This page documents the **public model outputs** currently exposed to API
consumers. It focuses on **field structure and meaning**.

For taxonomy-based outputs (for example: moods, genres, instruments), the
possible taxonomy values are listed in the
[Appendix: Taxonomy vocabularies](#appendix-taxonomy-vocabularies) for
reference.

---

## Example model output

The following example shows a taxonomy-based model output (MoodSimpleV2). It
demonstrates the common `scores` / `tags` / `segments` pattern.

The example is explained in the sections below (see
[Taxonomy classifiers](#taxonomy-classifiers-scores-segments-tags) and
[Track-level vs segment-level data](#track-level-vs-segment-level-data)).

```json
{
  "version": "MoodSimpleV2",
  "segments": {
    "timestampsSeconds": [5.0, 15.0, 25.0],
    "values": {
      "aggressive": [0.2172, 0.2986, 0.2332],
      "calm": [0.216, 0.1058, 0.2894],
      "chill": [0.1954, 0.0933, 0.0839],
      "dark": [0.4876, 0.2672, 0.5492],
      "energetic": [0.5873, 0.635, 0.2871],
      "epic": [0.0484, 0.2499, 0.0261],
      "happy": [0.2862, 0.136, 0.0894],
      "romantic": [0.0218, 0.0706, 0.0022],
      "sad": [0.2462, 0.0899, 0.3842],
      "scary": [0.3158, 0.0813, 0.2322],
      "sexy": [0.3539, 0.3665, 0.1121],
      "ethereal": [0.224, 0.1265, 0.2627],
      "uplifting": [0.3555, 0.428, 0.1668]
    }
  },
  "scores": {
    "aggressive": 0.2497,
    "calm": 0.2037,
    "chill": 0.1242,
    "dark": 0.4347,
    "energetic": 0.5032,
    "epic": 0.1082,
    "happy": 0.1705,
    "romantic": 0.0315,
    "sad": 0.2401,
    "scary": 0.2098,
    "sexy": 0.2775,
    "ethereal": 0.2044,
    "uplifting": 0.3168
  },
  "tags": ["energetic", "dark"]
}
```

## Versioning

Every model output object contains a `version` field.

The `version` is a discriminator (so you can pick the right schema), and it also
tracks **breaking changes** to the output structure. It defines:

- Which schema to expect (fields and types)
- Which taxonomy/vocabulary applies (for taxonomy-based outputs)

Multiple versions may exist at the same time. Older versions are deprecated over
time and API consumers should migrate to the latest available version when
possible.

---

## Track-level vs segment-level data

Many model outputs provide both:

- **Track-level results**: a single prediction for the whole track (e.g. `tag`,
  `scores`, `tags`).
- **Segment-level results**: predictions over time under `segments`.

Practical guidance:

- If you need **one value or descriptor for the track as a whole**, use the
  track-level fields (`tag`, `scores`, `tags`).
- If you need **how values evolve over the course of the track** (for example:
  where a mood becomes more intense), use `segments`.

Where present, segment-level data is represented as:

- `segments.timestampsSeconds`: array of segment start times (seconds from track
  start)
- `segments.values`: the segment values aligned by index with
  `timestampsSeconds`

The shape of `segments.values` depends on the model output:

- **Taxonomy classifiers**: `segments.values` is an object mapping taxonomy keys
  to arrays of scores.
- **Musical parameters**: `segments.values` is an array of predicted values.

In both cases, the array length(s) match `segments.timestampsSeconds.length`.

---

## Common field patterns

### Taxonomy classifiers (`scores`, `segments`, `tags`)

Many classifiers share the same structure:

- `scores`: object mapping **taxonomy keys** → track-level score (usually
  `0.0`-`1.0`), indicating the model's predicted probability for each tag.
- `segments`: segment-level scores over time.
- `tags`: array of the **dominant** taxonomy keys (a subset of the keys in
  `scores`).

For these model outputs, the precise set of taxonomy keys is fixed for the given
`version`.

### Musical parameters (`tag`, `segments`, `confidence`)

Musical parameter model outputs (e.g. BPM, key, time signature) expose:

- `tag`: the predicted global value for the whole track.
- `segments`: the predicted local values per segment.
- `confidence`: a structured confidence object with three values in `0.0`-`1.0`:
  - `modelCertainty`: how sure the model is that the predictions are correct
  - `predictionStability`: how stable the predictions are across segments
  - `confidence`: an overall confidence score, the minimum of the two individual
    scores

  **Interpretation**: Confidence values above `0.9` indicate the track is
  unambiguous and a single global label can be confidently applied.

---

## List of model outputs

The following model output versions are public (alphabetical):

- [AiMusicDetectionV1](#aimusicdetectionv1)
- [AudioFileInfoV1](#audiofileinfov1)
- [AugmentedKeywordsV3](#augmentedkeywordsv3)
- [AutoDescriptionV2](#autodescriptionv2)
- [BpmV2](#bpmv2)
- [CharacterV2](#characterv2)
- [FreeGenreV3](#freegenrev3)
- [InstrumentsV2](#instrumentsv2)
- [KeyV2](#keyv2)
- [MainGenreV2](#maingenrev2)
- [MoodAdvancedV2](#moodadvancedv2)
- [MoodSimpleV2](#moodsimplev2)
- [MovementV2](#movementv2)
- [MusicForV1](#musicforv1)
- [MusicalEraV2](#musicalerav2)
- [RepresentativeSegmentV2](#representativesegmentv2)
- [SubgenreV2](#subgenrev2)
- [TempoV1](#tempov1)
- [TimeSignatureV2](#timesignaturev2)
- [ValenceArousalV2](#valencearousalv2)
- [VocalsV2](#vocalsv2)
- [VocalStyleV1](#vocalstylev1)
- [VoiceoverV2](#voiceoverv2)

---

## AiMusicDetectionV1

Detects whether a track is likely AI-generated music.

Use this model to power UI scanning, filtering, or downstream policy decisions
where you want an estimate of whether a track was generated by an AI music
model.

Taxonomy: none

| Field            | Type           | Description                                                                                    |
| ---------------- | -------------- | ---------------------------------------------------------------------------------------------- |
| `version`        | string         | Always `"AiMusicDetectionV1"`.                                                                 |
| `isAiMusic`      | boolean        | `true` if the track is predicted as AI-generated music.                                        |
| `score`          | number         | Confidence-like score in `0.0`-`1.0`. Higher means more likely AI-generated.                   |
| `suspectedModel` | string \| null | Optional information about which generative model is suspected (if predicted as AI-generated). |

## AudioFileInfoV1

Technical properties of the provided audio file.

Taxonomy: none

| Field        | Type    | Description                                     |
| ------------ | ------- | ----------------------------------------------- |
| `version`    | string  | Always `"AudioFileInfoV1"`.                     |
| `duration`   | number  | Track duration in seconds.                      |
| `fileSizeB`  | integer | File size in bytes.                             |
| `bitrate`    | integer | Bitrate value as reported by decoding/metadata. |
| `samplerate` | integer | Sample rate in Hz.                              |

## AugmentedKeywordsV3

Keyword-like descriptors inferred from audio, represented as a weighted
dictionary.

Taxonomy: none

| Field     | Type   | Description                                                                                                |
| --------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| `version` | string | Always `"AugmentedKeywordsV3"`.                                                                            |
| `scores`  | object | Map of 20 highest scoring keyword identifiers → score in `-1.0`-`1.0` (higher means stronger association). |

## AutoDescriptionV2

A short natural-language description of the track.

This output is designed for human-facing UI (e.g. previews, catalog cards).
Treat it as generated text that may vary by model version.

Taxonomy: none

| Field         | Type   | Description                               |
| ------------- | ------ | ----------------------------------------- |
| `version`     | string | Always `"AutoDescriptionV2"`.             |
| `description` | string | Text description generated for the track. |

## BpmV2

Tempo in beats per minute (BPM).

Taxonomy: none

| Field                            | Type      | Description                                                                                                       |
| -------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------- |
| `version`                        | string    | Always `"BpmV2"`.                                                                                                 |
| `tag`                            | integer   | Track-level BPM estimate (constrained to `60`-`200`).                                                             |
| `segments`                       | object    | Segment-level BPM values.                                                                                         |
| `segments.timestampsSeconds`     | number[]  | Segment start times in seconds.                                                                                   |
| `segments.values`                | integer[] | BPM per segment (aligned with `timestampsSeconds`, `60`-`200`).                                                   |
| `confidence`                     | object    | Musical-parameter confidence object (all values `0.0`-`1.0`).                                                     |
| `confidence.modelCertainty`      | number    | How certain the model is in its local predictions.                                                                |
| `confidence.predictionStability` | number    | How stable the BPM is over time.                                                                                  |
| `confidence.confidence`          | number    | Overall confidence score. Values above `0.9` indicate the track is unambiguous and a single global label applies. |

## CharacterV2

High-level “character” descriptors (taxonomy-based classifier).

Use this model to describe the overall sonic “personality” of a track (e.g. for
playlisting, similarity, and creative search).

Taxonomy: [`CharacterV2Tags`](#characterv2tags)

| Field                        | Type     | Description                                                            |
| ---------------------------- | -------- | ---------------------------------------------------------------------- |
| `version`                    | string   | Always `"CharacterV2"`.                                                |
| `scores`                     | object   | Track-level scores (`0.0`-`1.0`) keyed by character tags.              |
| `tags`                       | string[] | Dominant character tags (subset of keys in `scores`).                  |
| `segments`                   | object   | Segment-level scores.                                                  |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                        |
| `segments.values`            | object   | Map of character tags → `number[]` (aligned with `timestampsSeconds`). |

## FreeGenreV3

Free-form genre tags without a fixed taxonomy.

Use this model when you want flexible genre labeling, including niche genres not
covered by a fixed taxonomy. Unlike taxonomy-based genre models, this output
does not provide per-tag scores.

Taxonomy: none

| Field     | Type     | Description                             |
| --------- | -------- | --------------------------------------- |
| `version` | string   | Always `"FreeGenreV3"`.                 |
| `tags`    | string[] | Free-text / free-vocabulary genre tags. |

## InstrumentsV2

Instrument presence classifier (taxonomy-based).

This model can be used to detect which instruments are present and how strongly,
and to localize those instruments over time via `segments`.

Taxonomy: [`InstrumentsV2Tags`](#instrumentsv2tags) (instruments),
[`InstrumentsV2PresenceTags`](#instrumentsv2presencetags) (presence categories)

| Field                        | Type     | Description                                                                             |
| ---------------------------- | -------- | --------------------------------------------------------------------------------------- |
| `version`                    | string   | Always `"InstrumentsV2"`.                                                               |
| `presence`                   | object   | Track-level instrument presence categories keyed by instrument identifier.              |
| `tags`                       | string[] | Detected instrument tags (subset of instrument taxonomy), sorted by amount of occurence |
| `segments`                   | object   | Segment-level instrument scores.                                                        |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                                         |
| `segments.values`            | object   | Map of instrument identifier → `number[]` scores (aligned with `timestampsSeconds`).    |

## KeyV2

Musical key prediction.

Taxonomy: [`KeyV2Tags`](#keyv2tags)

| Field                            | Type     | Description                                                                                                       |
| -------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `version`                        | string   | Always `"KeyV2"`.                                                                                                 |
| `tag`                            | string   | Track-level key detection from the KeyV2 taxonomy.                                                                |
| `segments`                       | object   | Segment-level key tags.                                                                                           |
| `segments.timestampsSeconds`     | number[] | Segment start times in seconds.                                                                                   |
| `segments.values`                | string[] | Key per segment (aligned with `timestampsSeconds`).                                                               |
| `confidence`                     | object   | Musical-parameter confidence object (all values `0.0`-`1.0`).                                                     |
| `confidence.modelCertainty`      | number   | Overall certainty of the key model.                                                                               |
| `confidence.predictionStability` | number   | How stable the key is over time.                                                                                  |
| `confidence.confidence`          | number   | Overall confidence score. Values above `0.9` indicate the track is unambiguous and a single global label applies. |

## MainGenreV2

Main genre classifier (taxonomy-based).

Use this model for high-level genre filtering and organization. For a more
specific genre classification, see `SubgenreV2` and `FreeGenreV3`.

Taxonomy: [`MainGenreV2Tags`](#maingenrev2tags)

| Field                        | Type     | Description                                                          |
| ---------------------------- | -------- | -------------------------------------------------------------------- |
| `version`                    | string   | Always `"MainGenreV2"`.                                              |
| `scores`                     | object   | Track-level scores (`0.0`-`1.0`) keyed by genre tags.                |
| `tags`                       | string[] | Dominant genre tags (subset of keys in `scores`).                    |
| `segments`                   | object   | Segment-level scores.                                                |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                      |
| `segments.values`            | object   | Map of genre → `number[]` scores (aligned with `timestampsSeconds`). |

## MoodAdvancedV2

Advanced mood classifier (taxonomy-based).

Use this model when you want a more fine-grained emotional description of the
track. If you prefer a smaller, simpler mood vocabulary, use `MoodSimpleV2`.

Taxonomy: [`MoodAdvancedV2Tags`](#moodadvancedv2tags)

| Field                        | Type     | Description                                                              |
| ---------------------------- | -------- | ------------------------------------------------------------------------ |
| `version`                    | string   | Always `"MoodAdvancedV2"`.                                               |
| `scores`                     | object   | Track-level scores (`0.0`-`1.0`) keyed by mood tags.                     |
| `tags`                       | string[] | Dominant mood tags (subset of keys in `scores`).                         |
| `segments`                   | object   | Segment-level scores.                                                    |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                          |
| `segments.values`            | object   | Map of mood tags → `number[]` scores (aligned with `timestampsSeconds`). |

## MoodSimpleV2

Simple mood classifier (taxonomy-based).

Use this model for a compact mood description that is easy to surface in UX and
filtering. For more granular moods, use `MoodAdvancedV2`.

Taxonomy: [`MoodSimpleV2Tags`](#moodsimplev2tags)

| Field                        | Type     | Description                                                              |
| ---------------------------- | -------- | ------------------------------------------------------------------------ |
| `version`                    | string   | Always `"MoodSimpleV2"`.                                                 |
| `scores`                     | object   | Track-level scores (`0.0`-`1.0`) keyed by mood tags.                     |
| `tags`                       | string[] | Dominant mood tags (subset of keys in `scores`).                         |
| `segments`                   | object   | Segment-level scores.                                                    |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                          |
| `segments.values`            | object   | Map of mood tags → `number[]` scores (aligned with `timestampsSeconds`). |

## MovementV2

Rhythmic “movement” classifier (taxonomy-based).

Use this model to describe rhythmic feel (groove / motion) beyond raw BPM. This
is often helpful for search and playlisting based on “feel”.

Taxonomy: [`MovementV2Tags`](#movementv2tags)

| Field                        | Type     | Description                                                                  |
| ---------------------------- | -------- | ---------------------------------------------------------------------------- |
| `version`                    | string   | Always `"MovementV2"`.                                                       |
| `scores`                     | object   | Track-level scores (`0.0`-`1.0`) keyed by movement tags.                     |
| `tags`                       | string[] | Dominant movement tags (subset of keys in `scores`).                         |
| `segments`                   | object   | Segment-level scores.                                                        |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                              |
| `segments.values`            | object   | Map of movement tags → `number[]` scores (aligned with `timestampsSeconds`). |

## MusicForV1

Use-case oriented tags indicating what the track is suitable for.

Use this model for “suitability” / “music for …” style metadata (e.g. mapping
tracks to use-cases in product UX or search).

Taxonomy: [`MusicForV1Tags`](#musicforv1tags)

| Field     | Type     | Description              |
| --------- | -------- | ------------------------ |
| `version` | string   | Always `"MusicForV1"`.   |
| `tags`    | string[] | Dominant music-for tags. |

## MusicalEraV2

Estimated production year and musical-era label.

Use this model to describe when a track sounds like it was produced (helpful for
era filtering and catalog metadata).

Taxonomy: [`MusicalEraV2Tags`](#musicalerav2tags)

| Field                     | Type    | Description                             |
| ------------------------- | ------- | --------------------------------------- |
| `version`                 | string  | Always `"MusicalEraV2"`.                |
| `estimatedProductionYear` | integer | Estimated year, from `1950`             |
| `tag`                     | string  | Era tag from the MusicalEraV2 taxonomy. |

## RepresentativeSegmentV2

The most representative segment of the track.

Use this model to pick a short segment that best represents the track overall
(e.g. for previews or highlighting). Taxonomy: none

| Field          | Type   | Description                                         |
| -------------- | ------ | --------------------------------------------------- |
| `version`      | string | Always `"RepresentativeSegmentV2"`.                 |
| `startSeconds` | number | Start time (seconds) of the representative segment. |
| `endSeconds`   | number | End time (seconds) of the representative segment.   |

## SubgenreV2

Subgenre classifier.

Use this model when you need a more specific classification than `MainGenreV2`.
If the track does not fit the subgenre taxonomy with sufficient confidence, the
output is `null`.

Subgenres are only detected within their corresponding parent-genre context; if
the track does not match any subgenre under that hierarchy, this output will be
`null`.

Taxonomy: [`SubgenreV2Tags`](#subgenrev2tags)

This model output can be `null`/missing (represented as `null` values for
`scores`, `tags`, and `segments`) when no subgenre can be determined with
sufficient confidence.

If `segments` is present, individual entries inside `segments.values` can still
be `null`.

| Field                        | Type             | Description                                                                     |
| ---------------------------- | ---------------- | ------------------------------------------------------------------------------- |
| `version`                    | string           | Always `"SubgenreV2"`.                                                          |
| `scores`                     | object \| null   | Track-level scores (`0.0`-`1.0`) keyed by subgenre tags.                        |
| `tags`                       | string[] \| null | Dominant subgenre tags.                                                         |
| `segments`                   | object \| null   | Segment-level scores.                                                           |
| `segments.timestampsSeconds` | number[]         | Segment start times in seconds (only present when `segments` is not `null`).    |
| `segments.values`            | object           | Map of subgenre → `number[] \| null` scores (aligned with `timestampsSeconds`). |

## TempoV1

High-level "perceived" tempo classification (taxonomy-based), plus a track-level
score.

Use this model when you want a coarse tempo label (fast/slow-style categories)
rather than a numeric BPM. For numeric tempo, use `BpmV2`.

Taxonomy: [`TempoV1Tags`](#tempov1tags)

| Field                        | Type     | Description                                                        |
| ---------------------------- | -------- | ------------------------------------------------------------------ |
| `version`                    | string   | Always `"TempoV1"`.                                                |
| `tag`                        | string   | Tempo tag from the TempoV1 taxonomy.                               |
| `score`                      | number   | Track-level score in `0.0`-`1.0` for the predicted `tag`.          |
| `segments`                   | object   | Segment-level tempo scores for the predicted tempo tag.            |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                    |
| `segments.values`            | number[] | Score per segment (`0.0`-`1.0`, aligned with `timestampsSeconds`). |

## TimeSignatureV2

Time signature prediction.

Use this model to determine the track’s meter (e.g. `4/4`, `3/4`).

Taxonomy: none

| Field                            | Type     | Description                                                                                                       |
| -------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `version`                        | string   | Always `"TimeSignatureV2"`.                                                                                       |
| `tag`                            | string   | Track-level time signature (e.g. `"4/4"`).                                                                        |
| `segments`                       | object   | Segment-level time signature values.                                                                              |
| `segments.timestampsSeconds`     | number[] | Segment start times in seconds.                                                                                   |
| `segments.values`                | string[] | Time signature per segment (aligned with `timestampsSeconds`).                                                    |
| `confidence`                     | object   | Musical-parameter confidence object (all values `0.0`-`1.0`).                                                     |
| `confidence.modelCertainty`      | number   | Overall certainty of the time signature model.                                                                    |
| `confidence.predictionStability` | number   | How stable the time signature is over time.                                                                       |
| `confidence.confidence`          | number   | Overall confidence score. Values above `0.9` indicate the track is unambiguous and a single global label applies. |

## ValenceArousalV2

Continuous emotional axes and derived categorical descriptors.

Use this model for continuous emotional metrics (valence/arousal) and for
derived, user-friendly categorical summaries such as energy and emotion-change
labels.

Taxonomy: [`ValenceArousalV2Tags`](#valencearousalv2tags) (axes),
[`ValenceArousalV2EnergyLevelTags`](#valencearousalv2energyleveltags),
[`ValenceArousalV2EnergyChangesTags`](#valencearousalv2energychangestags),
[`ValenceArousalV2EmotionProfileTags`](#valencearousalv2emotionprofiletags),
[`ValenceArousalV2EmotionChangesTags`](#valencearousalv2emotionchangestags)

| Field                        | Type     | Description                                                             |
| ---------------------------- | -------- | ----------------------------------------------------------------------- |
| `version`                    | string   | Always `"ValenceArousalV2"`.                                            |
| `scores`                     | object   | Track-level axis values (constrained to `-1.0`-`1.0`).                  |
| `segments`                   | object   | Segment-level axis values.                                              |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                         |
| `segments.values`            | object   | Map of axis key → `number[]` values (aligned with `timestampsSeconds`). |
| `energyLevel`                | string   | Overall energy level category.                                          |
| `energyChanges`              | string   | How much energy changes over time.                                      |
| `emotionProfile`             | string   | Overall emotional profile category.                                     |
| `emotionChanges`             | string   | How much emotion changes over time.                                     |

## VocalsV2

Vocal-characteristic classifier (taxonomy-based), with optional summary fields.

Use this model to understand whether and how much vocals are present and what
gender they resemble.

Taxonomy: [`VocalsV2Tags`](#vocalsv2tags),
[`VocalsV2PresenceTags`](#vocalsv2presencetags),
[`VocalsV2PredominantVocalGenderTags`](#vocalsv2predominantvocalgendertags)

| Field                        | Type           | Description                                                               |
| ---------------------------- | -------------- | ------------------------------------------------------------------------- |
| `version`                    | string         | Always `"VocalsV2"`.                                                      |
| `scores`                     | object         | Track-level scores (`0.0`-`1.0`) keyed by vocal tags.                     |
| `tags`                       | string[]       | Dominant vocal tags.                                                      |
| `segments`                   | object         | Segment-level scores.                                                     |
| `segments.timestampsSeconds` | number[]       | Segment start times in seconds.                                           |
| `segments.values`            | object         | Map of vocal tags → `number[]` scores (aligned with `timestampsSeconds`). |
| `vocalPresence`              | string \| null | Optional overall vocal presence label (if available).                     |
| `predominantVocalGender`     | string \| null | Optional predominant vocal gender label (if available).                   |

## VocalStyleV1

Vocal style classifier (taxonomy-based).

Use this model to describe the characteristics of present vocals in more detail
(useful for more specific vocal characterization beyond general vocals presence
and gender).

Taxonomy: [`VocalStyleV1Tags`](#vocalstylev1tags)

| Field                        | Type     | Description                                                                     |
| ---------------------------- | -------- | ------------------------------------------------------------------------------- |
| `version`                    | string   | Always `"VocalStyleV1"`.                                                        |
| `scores`                     | object   | Track-level scores (`0.0`-`1.0`) keyed by vocal-style tags.                     |
| `tags`                       | string[] | Dominant vocal-style tags.                                                      |
| `segments`                   | object   | Segment-level scores.                                                           |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                                 |
| `segments.values`            | object   | Map of vocal-style tags → `number[]` scores (aligned with `timestampsSeconds`). |

## VoiceoverV2

Voiceover detection and degree estimation.

Use this model to detect spoken-word / talkover content and to estimate how
dominant voiceover is across the track.

Taxonomy: none

| Field                        | Type     | Description                                                                   |
| ---------------------------- | -------- | ----------------------------------------------------------------------------- |
| `version`                    | string   | Always `"VoiceoverV2"`.                                                       |
| `voiceoverDegree`            | number   | Degree of voiceover dominance in `0.0`-`1.0`.                                 |
| `isVoiceoverDominant`        | boolean  | `true` if voiceover is dominant.                                              |
| `segments`                   | object   | Segment-level voiceover degree.                                               |
| `segments.timestampsSeconds` | number[] | Segment start times in seconds.                                               |
| `segments.values`            | number[] | Voiceover degree per segment (`0.0`-`1.0`, aligned with `timestampsSeconds`). |

---

## Appendix: Taxonomy vocabularies

The following taxonomies are referenced by the public model outputs above. They
are listed here as plain vocabularies (no explanations).

### CharacterV2Tags

<details>
<summary>Values</summary>

```text
bold
cool
epic
ethereal
heroic
luxurious
magical
mysterious
playful
powerful
retro
sophisticated
sparkling
sparse
unpolished
warm
```

</details>

### InstrumentsV2Tags

<details>
<summary>Values</summary>

```text
accordion
acousticGuitar
africanPercussion
asianFlute
asianStrings
banjo
bass
bassGuitar
bells
bongoConga
brass
celeste
cello
churchOrgan
clarinet
doubleBass
drumKit
electricGuitar
electricOrgan
electricPiano
electronicDrums
flute
horn
glockenspiel
harp
harpsichord
luteOud
mandolin
marimba
oboe
percussion
piano
pizzicato
saxophone
sitar
steelDrums
strings
synth
tabla
taiko
trumpet
tuba
ukulele
vibraphone
violin
whistling
woodwinds
```

</details>

### InstrumentsV2PresenceTags

<details>
<summary>Values</summary>

```text
absent
partially
frequently
throughout
```

</details>

### KeyV2Tags

<details>
<summary>Values</summary>

```text
aMajor
aMinor
bMajor
bMinor
bFlatMajor
bFlatMinor
cMajor
cMinor
dFlatMajor
cSharpMinor
dMajor
dMinor
eFlatMajor
dSharpMinor
eMajor
eMinor
fMajor
fMinor
fSharpMajor
fSharpMinor
gMajor
gMinor
aFlatMajor
gSharpMinor
```

</details>

### MainGenreV2Tags

<details>
<summary>Values</summary>

```text
african
ambient
middleEastern
asian
blues
childrenJingle
classical
electronic
folkCountry
funkSoul
indian
jazz
latin
metal
pop
rapHipHop
reggae
rnb
rock
singerSongwriter
sound
soundtrack
spokenWord
```

</details>

### MoodAdvancedV2Tags

<details>
<summary>Values</summary>

```text
adventurous
aggressive
agitated
angry
anthemic
anxious
aweInspiring
barren
bittersweet
blue
boingy
boisterous
bright
calm
celebratory
cheerful
cold
comedic
concerned
confident
contented
cool
courageous
creepy
dangerous
dark
delicate
depressing
determined
dignified
disturbing
dreamy
eccentric
eerie
emotional
energetic
epic
euphoric
evil
excited
exciting
exhilarating
fearful
feelGood
fiery
frightening
fun
funny
gloomy
graceful
happy
heavy
heroic
hopeful
horror
innocent
inspirational
intense
intimate
introspective
joyous
kind
laidBack
leisurely
light
lighthearted
lonely
loving
lyrical
majestic
melancholic
menacing
mischievous
motivational
mournful
mysterious
nervous
nightmarish
noble
nostalgic
ominous
optimistic
panicStricken
passionate
peaceful
perky
playful
poignant
ponderous
positive
powerful
prestigious
proud
quiet
quirky
reflective
relaxed
relentless
resolute
restless
rollicking
romantic
sad
scary
seductive
sentimental
serene
serious
sexy
soaring
soft
solemn
soothing
spiritual
spooky
strange
strong
supernatural
suspenseful
sweet
tender
tense
thoughtful
tranquil
triumphant
upbeat
uplifting
victorious
violent
warm
weird
whimsical
```

</details>

### MoodSimpleV2Tags

<details>
<summary>Values</summary>

```text
aggressive
calm
chill
dark
energetic
epic
happy
romantic
sad
scary
sexy
ethereal
uplifting
```

</details>

### MovementV2Tags

<details>
<summary>Values</summary>

```text
bouncing
driving
flowing
groovy
nonrhythmic
pulsing
robotic
running
steady
stomping
```

</details>

### MusicForV1Tags

<details>
<summary>Values</summary>

```text
achievement
action
adventure
advertising
alien
animation
animals
anniversary
anthem
anticipation
artInstallation
atmosphere
baby
backdrop
background
bar
barbecue
battle
beach
bedroom
branding
breakup
broadcast
building
bumper
business
cabaret
cafe
campaign
campfire
car
carChase
carol
cartoon
celebration
ceremony
chase
cheer
children
chillOut
choir
christmas
church
cinema
cinematic
circus
city
climax
closingCredits
club
coffeeShop
college
comedy
comingOfAge
commerce
commercial
community
competition
confidence
conflict
cooking
corporate
countryside
creativity
crime
crowd
cypher
dance
dancing
danger
darkness
dateNight
death
delight
desert
destruction
detective
dinner
discovery
djSet
documentary
drama
dream
drinks
drive
driving
education
elevator
empowerment
energy
engagement
enjoying
ensemble
entertainment
era
espionage
evening
event
exercise
explanation
exploration
fairyTale
faith
family
fantasy
farewell
farm
fashion
fashionShow
fear
festival
fight
film
fitness
flight
focus
freedom
friendship
funeral
future
gallery
gameTrailer
gaming
ghost
glory
goodTimes
grinding
gym
halloween
hero
highlights
historical
history
holiday
hollywood
home
horror
hotel
hunt
hype
immersion
improvisation
incidental
indie
infographic
infomercial
inspiration
installation
instrumental
intimacy
intrigue
intro
introspection
investigation
island
jingle
journey
jungle
karaoke
lecture
leisure
lifestyle
lobby
lookbook
loss
lounge
love
lullaby
luxury
meditation
memorial
memories
military
monster
montage
morning
motivation
motorsport
movie
museum
mystery
narration
narrative
nature
newYear
news
night
nightDrive
nightclub
nightlife
nostalgia
ocean
orchestra
outdoor
outro
parade
party
patriotism
performance
periodDrama
periodPiece
phobia
play
pleasure
podcast
presentation
promo
promotion
protest
pursuit
racing
radio
rain
rainyDay
rally
rave
reading
rebellion
recital
reel
rehearsal
relationship
relaxation
religion
restaurant
retro
roadTrip
robot
romance
sales
school
sciFi
science
sea
searching
shopping
show
singAlong
skateboarding
sleep
slideshow
smile
snow
soundDesign
soundEffects
soundscape
soundtrack
spa
space
sports
spring
spy
stinger
store
story
storytelling
street
study
summer
sunset
sunshine
superhero
suspense
teamwork
teaser
teen
television
theatre
thinking
thriller
timeLapse
title
trailer
training
transition
travel
tribute
triumph
tutorial
underscore
urban
vacation
videoGame
victory
vintage
vinyl
vlog
walk
walking
war
wedding
wellness
western
wildlife
winter
women
work
workout
worship
youth
youtube
zombie
```

</details>

### MusicalEraV2Tags

<details>
<summary>Values</summary>

```text
earlyMid1950s
midLate1950s
late1950sEarly1960s
earlyMid1960s
midLate1960s
late1960sEarly1970s
earlyMid1970s
midLate1970s
late1970sEarly1980s
earlyMid1980s
midLate1980s
late1980sEarly1990s
earlyMid1990s
midLate1990s
late1990sEarly2000s
earlyMid2000s
midLate2000s
late2000sEarly2010s
contemporary
```

</details>

### SubgenreV2Tags

<details>
<summary>Values</summary>

```text
abstractIdm
breakbeatDnb
deepHouse
electro
house
minimal
synthPop
techHouse
techno
trance
medievalPeriod
renaissancePeriod
baroquePeriod
classicalPeriod
romanticPeriod
contemporaryClassical
bluesRock
folkRock
hardRock
indieAlternative
psychProgRock
punk
rockAndRoll
popSoftRock
contemporaryRnb
gangsta
jazzyHipHop
popRap
trap
blackMetal
deathMetal
doomMetal
heavyMetal
metalcore
nuMetal
disco
funk
gospel
neoSoul
soul
bigBandSwing
bebop
contemporaryJazz
easyListening
fusion
latinJazz
smoothJazz
country
folk
```

</details>

### TempoV1Tags

<details>
<summary>Values</summary>

```text
slow
mediumSlow
medium
mediumFast
fast
```

</details>

### ValenceArousalV2Tags

<details>
<summary>Values</summary>

```text
valence
arousal
```

</details>

### ValenceArousalV2EnergyLevelTags

<details>
<summary>Values</summary>

```text
low
medium
high
varying
```

</details>

### ValenceArousalV2EnergyChangesTags

<details>
<summary>Values</summary>

```text
low
medium
high
```

</details>

### ValenceArousalV2EmotionProfileTags

<details>
<summary>Values</summary>

```text
negative
neutral
positive
varying
```

</details>

### ValenceArousalV2EmotionChangesTags

<details>
<summary>Values</summary>

```text
low
medium
high
```

</details>

### VocalsV2Tags

<details>
<summary>Values</summary>

```text
female
male
instrumental
```

</details>

### VocalsV2PresenceTags

<details>
<summary>Values</summary>

```text
low
medium
high
```

</details>

### VocalsV2PredominantVocalGenderTags

<details>
<summary>Values</summary>

```text
male
female
```

</details>

### VocalStyleV1Tags

<details>
<summary>Values</summary>

```text
femaleACapella
femaleChoir
femaleForegroundVocals
femaleBackgroundVocals
instrumental
maleACapella
maleChoir
maleForegroundVocals
maleBackgroundVocals
mixedACapella
mixedChoir
syntheticACapella
syntheticChoir
syntheticForegroundVocals
syntheticBackgroundVocals
```

</details>
