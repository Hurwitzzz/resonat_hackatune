import { useEffect, useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router-dom";
import GrainientBackground from "../components/GrainientBackground";
import NoteCard from "../components/NoteCard";
import PlaylistFan from "../components/PlaylistFan";
import Stack from "../components/Stack";
import Plus from "../components/icons/Plus";
import { useNotes } from "../context/NotesContext";
import { COVER_POOL, trackUrl, type SampleTrack } from "../sampleTracks";
import type { RecommendationCard } from "../api";

const displayTitle = (card: RecommendationCard) =>
  card.title || (card.track_id ? `Track ${card.track_id}` : "Recommended track");

const displayArtist = (card: RecommendationCard) =>
  card.artist || "Unknown artist";

// djb2 hash — spreads ids across the full cover pool far better than summing
// char codes (which collided constantly).
const hashString = (value: string) => {
  let hash = 5381;
  for (let i = 0; i < value.length; i++) {
    hash = ((hash << 5) + hash + value.charCodeAt(i)) >>> 0;
  }
  return hash;
};

const coverForCard = (card: RecommendationCard) => {
  const id = card.cyanite_id || card.track_id || "";
  return COVER_POOL[hashString(id) % COVER_POOL.length];
};

const toTrack = (card: RecommendationCard): SampleTrack => ({
  id: card.cyanite_id,
  trackId: card.track_id,
  title: displayTitle(card),
  artist: displayArtist(card),
  url: card.track_id ? trackUrl(card.track_id) : "",
  cover: coverForCard(card),
});

const ResultsPage = () => {
  const {
    notes,
    explanation,
    cards,
    sendFeedback,
    explainTrack,
    explanationsByTrackId,
  } = useNotes();
  const [isLeaving, setIsLeaving] = useState(false);
  const leaveTimer = useRef<number | null>(null);
  const navigate = useNavigate();
  const filledNotes = notes.filter((note) => note.body.trim());

  useEffect(
    () => () => {
      if (leaveTimer.current !== null) {
        window.clearTimeout(leaveTimer.current);
      }
    },
    [],
  );

  const handleSteer = () => {
    if (!document.startViewTransition) {
      setIsLeaving(true);
      leaveTimer.current = window.setTimeout(() => {
        navigate("/");
      }, 520);
      return;
    }

    document.startViewTransition(() => {
      flushSync(() => navigate("/"));
    });
  };

  // Assign covers deduped across the on-screen cards, so a replacement never
  // reuses a cover already showing (the pool is far larger than the visible
  // count). On a collision, probe forward through the pool for a free image.
  const tracks = useMemo(() => {
    const used = new Set<string>();
    return cards.map((card) => {
      const track = toTrack(card);
      let cover = track.cover;
      if (used.has(cover)) {
        const start = COVER_POOL.indexOf(cover);
        for (let k = 1; k < COVER_POOL.length; k++) {
          const candidate = COVER_POOL[(start + k) % COVER_POOL.length];
          if (!used.has(candidate)) {
            cover = candidate;
            break;
          }
        }
      }
      used.add(cover);
      return cover === track.cover ? track : { ...track, cover };
    });
  }, [cards]);

  // 自动预取解释：串行（一个完成再下一个，不齐发）+ 试过就不再自动重试（成败都记），
  // 否则失败的 track 会被 effect 反复重发，把 OpenAI 打到 429。手动重试走卡片的 onExplain。
  const attemptedRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      for (const track of tracks) {
        if (cancelled) return;
        if (explanationsByTrackId[track.id] || attemptedRef.current.has(track.id)) continue;
        attemptedRef.current.add(track.id);
        await explainTrack(track.id).catch(() => undefined);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [explainTrack, explanationsByTrackId, tracks]);

  return (
    <main
      className={`results-page-enter relative isolate flex min-h-screen w-full flex-col overflow-x-hidden bg-[var(--ink)] text-[var(--paper)] md:flex-row md:overflow-hidden ${
        isLeaving ? "results-page-leaving" : ""
      }`}
    >
      <GrainientBackground />

      {/* Left panel — the shrunk taste board. */}
      <aside className="relative z-10 flex w-full shrink-0 flex-col overflow-y-auto border-b border-[var(--color-border)] p-5 md:h-screen md:w-96 md:border-b-0 md:border-r">
        <h2 className="font-display mb-5 text-[24px] font-bold uppercase leading-none text-[var(--paper)]">
          Your taste board
        </h2>

        {/* Draggable-free card stack of the brief's memos (click to cycle). */}
        {filledNotes.length > 0 && (
          <div className="mx-auto h-[210px] w-full max-w-[280px]">
            <Stack
              randomRotation
              sendToBackOnClick
              cards={filledNotes.map((note, index) => (
                <NoteCard
                  key={note.id}
                  note={note}
                  index={index}
                  widthClass="w-full"
                  fill
                  readOnly
                  viewTransitionName={`note-${note.id}`}
                />
              ))}
            />
          </div>
        )}

        {/* "steer…" — go back to the start page to refine the board. */}
        <button
          type="button"
          onClick={handleSteer}
          disabled={isLeaving}
          className="steer-button font-display mt-6 flex min-h-11 w-full items-center gap-2 rounded-full border-[2.5px] border-solid border-[var(--paper)] px-5 py-3 text-left text-[16px] font-bold uppercase leading-[1.4] text-[var(--paper)] transition-colors hover:border-[var(--yellow)] hover:bg-[var(--yellow)] hover:text-[var(--ink)] disabled:cursor-default md:mt-auto"
        >
          <Plus size={18} />
          <span>steer...</span>
        </button>
      </aside>

      {/* Right panel — the playlist. */}
      <section className="relative z-10 w-full flex-1 overflow-y-auto p-6 md:p-10">
        <h1 className="font-display max-w-3xl text-[28px] font-bold uppercase leading-none tracking-[-0.01em] text-[var(--paper)]">
          A playlist built from your memo
        </h1>

        <div className="mt-8">
          {tracks.length > 0 ? (
            <PlaylistFan
              tracks={tracks}
              onLike={(track) => sendFeedback(track.id, "like")}
              onDismiss={(track) => sendFeedback(track.id, "dislike")}
              onExplain={async (track) => {
                const result = await explainTrack(track.id);
                return result.why_text;
              }}
            />
          ) : (
            <p className="font-serif text-[24px] italic text-[var(--paper)] opacity-80">
              No recommendations loaded yet. Steer back and find your sound again.
            </p>
          )}
        </div>

        {explanation && (
          <p className="font-serif mt-8 max-w-3xl text-[22px] italic leading-[1.25] text-[var(--paper)]">
            {explanation}
          </p>
        )}
      </section>
    </main>
  );
};

export default ResultsPage;
