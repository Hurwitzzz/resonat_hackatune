import { useEffect, useState } from "react";
import heroArt from "../assets/hero.png";

const REASON_TEXT =
  "This track found you because your sound brief points toward something warm, unhurried, and emotionally close. The recommendation balances soft rhythm, late-night texture, and a gentle lift so the song feels personal without pulling you out of the mood you described.";

interface TrackReasonModalProps {
  track: MusicCardsTrack;
  reasonText?: string;
  isLoading?: boolean;
  onClose: () => void;
}

const TrackReasonModal = ({
  track,
  reasonText = REASON_TEXT,
  isLoading = false,
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
          <p className="font-serif mt-6 min-h-40 text-[18px] leading-[1.6] text-[var(--ink)]">
            {visibleText}
            {visibleTokens < tokens.length && (
              <span className="ml-1 inline-block h-5 w-2 animate-pulse rounded-sm bg-[var(--blue)] align-middle" />
            )}
          </p>
        </div>
      </section>
    </div>
  );
};

export default TrackReasonModal;
