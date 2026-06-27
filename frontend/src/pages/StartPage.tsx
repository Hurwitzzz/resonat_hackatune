import { useEffect, useRef, useState } from "react";
import type { Note } from "../types";
import type { QueryCard } from "../api";
import { intent, confirm as confirmCard } from "../api";
import Canvas from "../components/Canvas";
import Controls from "../components/Controls";
import NoteCard from "../components/NoteCard";
import Slogan from "../components/Slogan";
import Plus from "../components/icons/Plus";

const GREETING = "Hi, What should today sound like?";

const joinNotes = (notes: Note[]): string =>
  notes
    .map((note) => note.body.trim())
    .filter(Boolean)
    .join("; ");

// Placeholder "sound briefs" for front-end testing while the backend (/intent)
// isn't wired up. A random one is shown each time editing finishes.
const PSEUDO_EXPLANATIONS = [
  "A warm, relaxed summer-evening playlist, calm, chilled, flowing and acoustic, with low-medium energy to cool you down without feeling sleepy.",
  "A cozy late-night wind-down set, soft, intimate and acoustic, with gentle low energy to help you unwind without drifting off.",
  "An upbeat sunny-morning mix, bright, breezy and rhythmic, with medium-high energy to get you moving.",
  "A focused deep-work soundtrack, steady, minimal and atmospheric, with calm mid energy to keep you in flow.",
  "A nostalgic rainy-day playlist, mellow, warm and a little melancholic, with soft low energy and plenty of space.",
];

// Local fallback used when the backend (/intent) isn't reachable, so the
// front end stays testable on its own.
const buildPseudoExplanation = (notes: Note[]): string => {
  if (!joinNotes(notes)) return "";
  const index = Math.floor(Math.random() * PSEUDO_EXPLANATIONS.length);
  return PSEUDO_EXPLANATIONS[index];
};

const StartPage = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [explanation, setExplanation] = useState("");
  const [card, setCard] = useState<QueryCard | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const isEmpty = notes.length === 0;

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

  // "Finish edit": compile the post-its into an explanation via /intent,
  // falling back to a local pseudo explanation when the backend is offline.
  const finishEditing = async () => {
    clearIdleTimer();
    const text = joinNotes(notesRef.current);
    if (!text) {
      setCard(null);
      setExplanation("");
      return;
    }
    try {
      const result = await intent(text);
      setCard(result);
      setExplanation(result.interpretation_plain);
    } catch {
      // Backend not running — show the local pseudo explanation instead.
      setCard(null);
      setExplanation(buildPseudoExplanation(notesRef.current));
    }
  };

  const addNote = () => {
    setNotes((prev) => [...prev, { id: crypto.randomUUID(), body: "" }]);
  };

  const updateNote = (id: string, body: string) => {
    setNotes((prev) =>
      prev.map((note) => (note.id === id ? { ...note, body } : note)),
    );
    // Finish editing if the user stops typing for 3 seconds.
    clearIdleTimer();
    idleTimer.current = window.setTimeout(() => {
      void finishEditing();
    }, 3000);
  };

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2500);
  };

  const handleNextStep = async () => {
    const prompts = notesRef.current
      .map((note) => note.body.trim())
      .filter(Boolean);
    if (prompts.length === 0) {
      showToast("Add a note first to describe the music you want.");
      return;
    }
    console.log("Music prompts:", prompts);
    console.log(
      "Explanation:",
      explanation || buildPseudoExplanation(notesRef.current),
    );
    // If a Query Card was compiled, confirm it to kick off the search.
    if (card) {
      try {
        const res = await confirmCard(card);
        console.log("Confirmed session:", res.session_id, "cards:", res.cards);
        showToast(`Searching… ${res.cards.length} candidate(s).`);
        return;
      } catch {
        // Backend offline — fall through to the offline toast below.
      }
    }
    showToast(
      `Captured ${prompts.length} prompt${prompts.length === 1 ? "" : "s"}.`,
    );
  };

  return (
    <main className="relative min-h-screen w-full">
      <Canvas>
        <div className="flex min-h-screen flex-col items-center justify-center gap-10 p-12">
          {/* Center text: greeting at the start, the explanation once editing finishes. */}
          {explanation ? (
            <div className="max-w-2xl text-center">
              <p className="mb-2 text-sm font-semibold text-indigo-300/80">
                We translated your note into a sound brief.
              </p>
              <p className="text-lg leading-relaxed text-white/80">
                {explanation}
              </p>
            </div>
          ) : (
            <h1 className="max-w-2xl text-center text-3xl font-medium text-white/85 sm:text-4xl">
              {GREETING}
            </h1>
          )}

          {/* Notes cluster — centered, wrapping, non-overlapping. */}
          {!isEmpty && (
            <div className="flex max-w-5xl flex-wrap items-start justify-center gap-8">
              {notes.map((note, index) => (
                <NoteCard
                  key={note.id}
                  note={note}
                  index={index}
                  onChange={updateNote}
                  onFinishEdit={() => void finishEditing()}
                />
              ))}
            </div>
          )}

          {/* Starting state: add button centered beneath the greeting. */}
          {isEmpty && (
            <button
              type="button"
              onClick={addNote}
              aria-label="Add a note"
              title="Add a note"
              className="flex h-16 w-16 items-center justify-center rounded-full bg-[#35363e] text-white/90 shadow-lg transition-transform duration-300 hover:scale-110 hover:text-white"
            >
              <Plus size={30} />
            </button>
          )}
        </div>
      </Canvas>

      <Slogan />

      {/* Once notes exist, the add button lives in the left sidebar. */}
      {!isEmpty && <Controls onAdd={addNote} />}

      <button
        type="button"
        onClick={() => void handleNextStep()}
        className="fixed bottom-6 right-6 z-[10000] rounded-full bg-indigo-500 px-6 py-3 text-base font-semibold text-white shadow-lg transition-colors hover:bg-indigo-400"
      >
        Find my sound →
      </button>

      {toast && (
        <div
          role="status"
          className="fixed bottom-24 right-6 z-[10000] rounded-lg bg-[#35363e] px-4 py-2 text-sm text-white/90 shadow-lg"
        >
          {toast}
        </div>
      )}
    </main>
  );
};

export default StartPage;
