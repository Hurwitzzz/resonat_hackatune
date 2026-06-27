// Pastel post-it themes borrowed from the Sticky-Notes-React reference.
// We don't expose a color picker — each note is assigned one of these
// deterministically by its position so the board stays colorful.
export interface NoteColor {
  header: string;
  body: string;
  text: string;
}

export const NOTE_COLORS: NoteColor[] = [
  { header: "#FFEFBE", body: "#FFF5DF", text: "#18181A" }, // yellow
  { header: "#AFDA9F", body: "#BCDEAF", text: "#18181A" }, // green
  { header: "#9BD1DE", body: "#A6DCE9", text: "#18181A" }, // blue
  { header: "#FED0FD", body: "#FEE5FD", text: "#18181A" }, // purple
];

export const colorForIndex = (index: number): NoteColor =>
  NOTE_COLORS[index % NOTE_COLORS.length];
