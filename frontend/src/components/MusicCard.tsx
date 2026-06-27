import { useState, type KeyboardEvent, type MouseEvent } from "react";
import ThumbsUp from "./icons/ThumbsUp";
import ThumbsDown from "./icons/ThumbsDown";

type Verdict = "like" | "dislike" | null;

interface MusicCardProps {
  // The card is the chosen/front one in the fan — show its feedback controls.
  active?: boolean;
  onOpen?: () => void;
  title?: string;
  artist?: string;
  isPlaying?: boolean;
  unavailable?: boolean;
}

// Animated "now playing" equalizer cue (there is no play/pause button).
const NowPlaying = () => (
  <span aria-label="Now playing" className="flex items-end gap-[3px]">
    {[0, 1, 2].map((bar) => (
      <span
        key={bar}
        className="w-[3px] animate-bounce rounded-sm bg-[var(--ink)]"
        style={{ height: 8 + bar * 4, animationDelay: `${bar * 120}ms` }}
      />
    ))}
  </span>
);

// Track card with hover-driven playback. Will later host a real music widget
// and map the thumbs to feedback(session_id, track_id, "like"|"dislike").
const MusicCard = ({
  active = false,
  onOpen,
  title,
  artist,
  isPlaying = false,
  unavailable = false,
}: MusicCardProps) => {
  const [verdict, setVerdict] = useState<Verdict>(null);

  // Clicking the active verdict again clears it back to neutral.
  const toggle = (next: Exclude<Verdict, null>) =>
    setVerdict((prev) => (prev === next ? null : next));

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    onOpen?.();
  };

  const handleVerdictClick = (
    event: MouseEvent<HTMLButtonElement>,
    next: Exclude<Verdict, null>,
  ) => {
    event.stopPropagation();
    toggle(next);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={handleKeyDown}
      aria-label="Open track explanation"
      className="flex h-full w-full flex-col rounded-[10px] bg-[var(--paper)] p-4 text-[var(--ink)] shadow-[var(--shadow-block)] outline-none transition duration-150 hover:-translate-y-0.5"
    >
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center">
        {isPlaying && !unavailable && <NowPlaying />}
        <span className="font-serif text-[26px] italic leading-[1.1] text-[var(--ink)]">
          {title ?? "playing... music widget"}
        </span>
        {artist && (
          <span className="font-display text-[12px] font-bold uppercase tracking-[0.08em] text-[var(--ink)] opacity-60">
            {artist}
          </span>
        )}
        {unavailable && (
          <span className="font-display text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--red)]">
            unavailable
          </span>
        )}
      </div>

      {active && (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={(event) => handleVerdictClick(event, "like")}
            aria-label="Thumbs up"
            aria-pressed={verdict === "like"}
            title="I like this"
            className={`flex h-11 w-11 items-center justify-center rounded-full border-[2.5px] transition-colors ${
              verdict === "like"
                ? "border-[var(--green)] bg-[var(--green)] text-[var(--paper)]"
                : "border-[var(--ink)] text-[var(--ink)] hover:bg-[var(--yellow)]"
            }`}
          >
            <ThumbsUp size={18} />
          </button>
          <button
            type="button"
            onClick={(event) => handleVerdictClick(event, "dislike")}
            aria-label="Thumbs down"
            aria-pressed={verdict === "dislike"}
            title="Not for me"
            className={`flex h-11 w-11 items-center justify-center rounded-full border-[2.5px] transition-colors ${
              verdict === "dislike"
                ? "border-[var(--red)] bg-[var(--red)] text-[var(--paper)]"
                : "border-[var(--ink)] text-[var(--ink)] hover:bg-[var(--pink)]"
            }`}
          >
            <ThumbsDown size={18} />
          </button>
        </div>
      )}
    </div>
  );
};

export default MusicCard;
