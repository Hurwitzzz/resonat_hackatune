import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import type { Note } from "../types";
import type {
  ExplanationResponse,
  FeedbackMode,
  QueryCard,
  RecommendationCard,
} from "../api";
import { confirm, explain, feedback, intent } from "../api";

const joinNotes = (notes: Note[]): string =>
  notes
    .map((note) => note.body.trim())
    .filter(Boolean)
    .join("; ");

const MAX_NOTES = 6;
// Local fallback used when the backend (/intent) isn't reachable, so the
// front end stays testable on its own.
const buildPseudoExplanation = (notes: Note[]): string => {
  const text = joinNotes(notes);
  if (!text) return "";
  return `A search for music shaped around: ${text}. We'll prioritize tracks whose mood, energy, instrumentation, and vocal presence match that brief.`;
};

interface NotesContextValue {
  notes: Note[];
  explanation: string;
  card: QueryCard | null;
  sessionId: string | null;
  cards: RecommendationCard[];
  likedCards: RecommendationCard[];
  isLoadingCards: boolean;
  cardsError: string;
  confirmSound: () => Promise<boolean>;
  sendFeedback: (
    trackId: string,
    verdict: "like" | "dislike",
    mode?: FeedbackMode,
  ) => Promise<void>;
  unlikeTrack: (trackId: string) => void;
  explainTrack: (trackId: string) => Promise<ExplanationResponse>;
  explanationsByTrackId: Record<string, ExplanationResponse>;
  addNote: () => void;
  updateNote: (id: string, body: string) => void;
  finishEditing: () => void;
  buildPseudoExplanation: (notes: Note[]) => string;
}

const NotesContext = createContext<NotesContextValue | null>(null);

export const NotesProvider = ({ children }: { children: ReactNode }) => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [explanation, setExplanation] = useState("");
  const [card, setCard] = useState<QueryCard | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [cards, setCards] = useState<RecommendationCard[]>([]);
  const [likedCards, setLikedCards] = useState<RecommendationCard[]>([]);
  const [isLoadingCards, setIsLoadingCards] = useState(false);
  const [cardsError, setCardsError] = useState("");
  const [explanationsByTrackId, setExplanationsByTrackId] = useState<
    Record<string, ExplanationResponse>
  >({});

  // Keep a live ref to notes so the idle timer / blur handler read fresh content.
  const notesRef = useRef(notes);
  useEffect(() => {
    notesRef.current = notes;
  }, [notes]);

  // 3-second "stopped typing" timer.
  const idleTimer = useRef<number | null>(null);
  const clearIdleTimer = () => {
    if (idleTimer.current !== null) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = null;
    }
  };
  useEffect(() => clearIdleTimer, []);

  // "Finish edit": compile the memos into an explanation via /intent,
  // falling back to a local pseudo explanation when the backend is offline.
  const finishEditing = async (): Promise<string | null> => {
    clearIdleTimer();
    const text = joinNotes(notesRef.current);
    if (!text) {
      setCard(null);
      setExplanation("");
      setSessionId(null);
      setCards([]);
      setLikedCards([]);
      setCardsError("");
      setExplanationsByTrackId({});
      return null;
    }
    try {
      const result = await intent(text);
      setSessionId(result.session_id);
      setCard(result.query_card);
      setCards([]);
      setLikedCards([]);
      setCardsError("");
      setExplanationsByTrackId({});
      setExplanation(result.query_card.interpretation_plain);
      return result.session_id;
    } catch {
      // Backend not running — show the local pseudo explanation instead.
      setCard(null);
      setExplanation(buildPseudoExplanation(notesRef.current));
      return null;
    }
  };

  const confirmSound = async () => {
    let activeSessionId = sessionId;
    if (!activeSessionId) {
      activeSessionId = await finishEditing();
    }
    if (!activeSessionId) return false;
    setIsLoadingCards(true);
    setCardsError("");
    try {
      const result = await confirm(activeSessionId);
      setCards(result.cards);
      return result.cards.length > 0;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load recommendations.";
      setCards([]);
      setCardsError(message);
      throw new Error(message);
    } finally {
      setIsLoadingCards(false);
    }
  };

  const sendFeedback = async (
    trackId: string,
    verdict: "like" | "dislike",
    mode: FeedbackMode = "normal",
  ) => {
    if (!sessionId) return;
    if (verdict === "like") {
      const liked = cards.find(
        (card) => card.cyanite_id === trackId || card.track_id === trackId,
      );
      if (liked) {
        setLikedCards((prev) =>
          prev.some((card) => card.cyanite_id === liked.cyanite_id)
            ? prev
            : [...prev, liked],
        );
      }
    }
    const result = await feedback(sessionId, trackId, verdict, mode);
    setCards(result.cards);
    if (verdict === "dislike" || mode === "normal") {
      setExplanationsByTrackId((prev) => {
        const next = { ...prev };
        delete next[trackId];
        return next;
      });
    }
  };

  const unlikeTrack = (trackId: string) => {
    setLikedCards((prev) =>
      prev.filter(
        (card) => card.cyanite_id !== trackId && card.track_id !== trackId,
      ),
    );
  };

  const explainTrack = async (trackId: string) => {
    const cached = explanationsByTrackId[trackId];
    if (cached) return cached;
    if (!sessionId) throw new Error("No active session");
    const result = await explain(sessionId, trackId);
    setExplanationsByTrackId((prev) => ({ ...prev, [trackId]: result }));
    return result;
  };

  const addNote = () => {
    setNotes((prev) =>
      prev.length >= MAX_NOTES
        ? prev
        : [
            ...prev,
            {
              id: crypto.randomUUID(),
              body: "",
              createdAt: new Date().toISOString(),
            },
          ],
    );
  };

  const updateNote = (id: string, body: string) => {
    setNotes((prev) =>
      prev.map((note) => (note.id === id ? { ...note, body } : note)),
    );
    setSessionId(null);
    setCards([]);
    setLikedCards([]);
    setCardsError("");
    setExplanationsByTrackId({});
    // Finish editing if the user stops typing for 3 seconds.
    clearIdleTimer();
    idleTimer.current = window.setTimeout(() => {
      void finishEditing();
    }, 3000);
  };

  const value: NotesContextValue = {
    notes,
    explanation,
    card,
    sessionId,
    cards,
    likedCards,
    isLoadingCards,
    cardsError,
    confirmSound,
    sendFeedback,
    unlikeTrack,
    explainTrack,
    explanationsByTrackId,
    addNote,
    updateNote,
    finishEditing: () => void finishEditing(),
    buildPseudoExplanation,
  };

  return (
    <NotesContext.Provider value={value}>{children}</NotesContext.Provider>
  );
};

// eslint-disable-next-line react/only-export-components
export const useNotes = (): NotesContextValue => {
  const ctx = useContext(NotesContext);
  if (!ctx) {
    throw new Error("useNotes must be used within a NotesProvider");
  }
  return ctx;
};
