// 后端 4 端点的 typed 封装。base 走 Vite 代理（见 vite.config.ts）。
const BASE = "/api";

export type SoftTarget = { dim: string; value: string; weight: number };
export type QueryCard = {
  interpretation_plain: string;
  free_text_query: string;
  soft_targets: SoftTarget[];
  negatives: Record<string, unknown>[];
};
export type IntentResponse = {
  session_id: string;
  whiteboard_posts: unknown[];
  query_card: QueryCard;
};
export type RecommendationCard = {
  track_id: string;
  cyanite_id: string;
  title: string;
  artist: string;
  source: string;
  score: number;
  why?: string;
};
export type CardsResponse = {
  cards: RecommendationCard[];
  candidate_pool_size: number;
};
export type ExplanationResponse = {
  why_text: string;
  evidence: { source: string; detail: string }[];
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

export const intent = (text: string, user_id = "demo") =>
  post<IntentResponse>("/intent", { text, user_id });

export const confirm = (session_id: string) =>
  post<CardsResponse>("/intent/confirm", { session_id });

export const feedback = (session_id: string, track_id: string, verdict: "like" | "dislike") =>
  post<CardsResponse>("/feedback", { session_id, track_id, verdict });

export const explain = (session_id: string, track_id: string) =>
  post<ExplanationResponse>("/explain", { session_id, track_id });

export const yourSound = (user_id = "demo") =>
  fetch(`${BASE}/your-sound?user_id=${user_id}`).then((r) => r.json());
