// Self-contained heart "like" particle burst (ported from the music-cards
// reference, but with inline styles so it needs no external CSS). Respects
// prefers-reduced-motion.
export function particleBurst(x: number, y: number, color = "#ED2024") {
  if (typeof document === "undefined") return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

  const N = 16;
  for (let i = 0; i < N; i++) {
    const p = document.createElement("div");
    const size = 4 + Math.random() * 5;
    Object.assign(p.style, {
      position: "fixed",
      left: `${x}px`,
      top: `${y}px`,
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: "50%",
      background: color,
      pointerEvents: "none",
      zIndex: "30000",
      willChange: "transform, opacity",
    });
    document.body.appendChild(p);

    const angle = (i / N) * Math.PI * 2 + Math.random() * 0.5;
    const dist = 24 + Math.random() * 34;
    const dx = Math.cos(angle) * dist;
    const dy = Math.sin(angle) * dist;
    const duration = 550 + Math.random() * 350;

    p.animate(
      [
        { transform: "translate(-50%,-50%) translate(0,0) scale(1)", opacity: 1 },
        {
          transform: `translate(-50%,-50%) translate(${dx}px,${dy + 10}px) scale(0)`,
          opacity: 0,
        },
      ],
      { duration, easing: "cubic-bezier(.18,.7,.3,1)", fill: "forwards" },
    );
    window.setTimeout(() => p.remove(), duration + 60);
  }
}

// Festive multi-color confetti burst for the "surprise" card celebration.
const CELEBRATION_COLORS = ["#ED2024", "#189A4C", "#F45CA0", "#2C5BC7", "#F6B400"];

export function celebrationBurst(x: number, y: number) {
  if (typeof document === "undefined") return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

  const N = 28;
  for (let i = 0; i < N; i++) {
    const p = document.createElement("div");
    const size = 5 + Math.random() * 7;
    Object.assign(p.style, {
      position: "fixed",
      left: `${x}px`,
      top: `${y}px`,
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: Math.random() > 0.5 ? "50%" : "1px",
      background: CELEBRATION_COLORS[i % CELEBRATION_COLORS.length],
      pointerEvents: "none",
      zIndex: "30000",
      willChange: "transform, opacity",
    });
    document.body.appendChild(p);

    const angle = (i / N) * Math.PI * 2 + Math.random() * 0.6;
    const dist = 40 + Math.random() * 70;
    const dx = Math.cos(angle) * dist;
    const dy = Math.sin(angle) * dist;
    const rot = (Math.random() * 2 - 1) * 220;
    const duration = 700 + Math.random() * 500;

    p.animate(
      [
        {
          transform: "translate(-50%,-50%) translate(0,0) rotate(0) scale(1)",
          opacity: 1,
        },
        {
          transform: `translate(-50%,-50%) translate(${dx}px,${dy + 24}px) rotate(${rot}deg) scale(0.2)`,
          opacity: 0,
        },
      ],
      { duration, easing: "cubic-bezier(.16,.7,.3,1)", fill: "forwards" },
    );
    window.setTimeout(() => p.remove(), duration + 80);
  }
}
