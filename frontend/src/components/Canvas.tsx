import type { ReactNode } from "react";

interface CanvasProps {
  children: ReactNode;
}

// The dark "board" with a subtle grid background.
const Canvas = ({ children }: CanvasProps) => (
  <div className="canvas-grid min-h-screen w-full">{children}</div>
);

export default Canvas;
