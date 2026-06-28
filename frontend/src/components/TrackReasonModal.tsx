import { useEffect, useState } from "react";
import heroArt from "../assets/hero.png";

interface TrackReasonModalProps {
  track: MusicCardsTrack;
  reasonText?: string;
  isLoading?: boolean;
  requested?: boolean;
  onRequestReason?: () => void;
  onClose: () => void;
}

const TrackReasonModal = ({
  track,
  reasonText = "",
  isLoading = false,
  requested = false,
  onRequestReason,
  onClose,
}: TrackReasonModalProps) => {
  const [visibleTokens, setVisibleTokens] = useState(0);
  const tokens = (isLoading ? "Finding the musical evidence..." : reasonText).match(/\S+\s*/g) ?? [];
  const visibleText = tokens.slice(0, visibleTokens).join("");

  useEffect(() => {
    setVisibleTokens(0);
    const timer = window.setInterval(() => {
      setVisibleTokens((count) => {
        if (count >= tokens.length) {
          window.clearInterval(timer);
          return count;
        }
        return count + 1;
      });
    }, 42);

    return () => window.clearInterval(timer);
  }, [track, tokens.length]);

  return (
    <div
      className="fixed inset-0 z-[20000] flex items-center justify-center bg-[rgba(27,27,27,.88)] p-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="track-reason-title"
        onClick={(event) => event.stopPropagation()}
        className="grid w-full max-w-5xl grid-cols-1 gap-8 rounded-[10px] bg-[var(--paper)] p-8 text-[var(--ink)] shadow-[var(--shadow-block)] md:grid-cols-[0.9fr_1.1fr]"
      >
        <div className="aspect-square overflow-hidden rounded-[10px] bg-[var(--ink)]">
          <img
            src={track.cover ?? heroArt}
            alt="Recommended track artwork"
            className="h-full w-full object-cover"
          />
        </div>

        <div className="flex min-h-80 flex-col justify-center">
          <p className="font-display text-[13px] font-bold uppercase tracking-[0.08em] text-[var(--ink)] opacity-60">
            {track.track} · {track.artist}
          </p>
          <h2
            id="track-reason-title"
            className="font-display mt-2 whitespace-nowrap text-[30px] font-bold leading-none sm:text-[36px]"
          >
            why this song found you
          </h2>
          {requested ? (
            <p className="font-serif mt-6 min-h-40 text-[18px] leading-[1.6] text-[var(--ink)]">
              {visibleText}
              {visibleTokens < tokens.length && (
                <span className="ml-1 inline-block h-5 w-2 animate-pulse rounded-sm bg-[var(--blue)] align-middle" />
              )}
            </p>
          ) : (
            <div className="mt-6 flex min-h-40 flex-col items-start justify-center">
              <button
                type="button"
                onClick={onRequestReason}
                className="font-display rounded-full border-[2.5px] border-solid border-[var(--ink)] px-6 py-3 text-[16px] font-bold uppercase leading-[1.4] text-[var(--ink)] transition-colors hover:border-[var(--yellow)] hover:bg-[var(--yellow)]"
              >
                why this song? →
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default TrackReasonModal;
