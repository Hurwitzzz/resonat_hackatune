import { useEffect, useMemo, useState } from "react";

const SENTENCE_MS = 2600;

const splitSentences = (text: string) => {
  const matches = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [];
  return matches.map((part) => part.trim()).filter(Boolean);
};

interface IntentBriefTickerProps {
  text: string;
}

const IntentBriefTicker = ({ text }: IntentBriefTickerProps) => {
  const [index, setIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const sentences = useMemo(() => splitSentences(text), [text]);
  const visibleText = expanded ? text : sentences[index] || text;

  useEffect(() => {
    setIndex(0);
    setExpanded(false);
  }, [text]);

  useEffect(() => {
    if (expanded || sentences.length <= 1) return;
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % sentences.length);
    }, SENTENCE_MS);
    return () => window.clearInterval(timer);
  }, [expanded, sentences.length]);

  return (
    <button
      type="button"
      aria-expanded={expanded}
      aria-label={expanded ? "Collapse sound brief" : "Expand sound brief"}
      onClick={() => setExpanded((current) => !current)}
      className="font-serif mx-auto block max-w-3xl text-center text-[28px] italic leading-[1.22] text-[var(--paper)] transition-opacity hover:opacity-90 sm:text-[32px]"
    >
      <span key={`${expanded}-${index}-${text}`}>
        {visibleText}
      </span>
    </button>
  );
};

export default IntentBriefTicker;
