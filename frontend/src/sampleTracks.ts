// Temporary sample tracks for testing playback. Real cards will come from the
// backend's confirm()/feedback() later. These are real rows from
// data/tracks.csv, verified to return valid MP3s from Jamendo.

export interface SampleTrack {
  id: string;
  title: string;
  artist: string;
  url: string;
}

// Mirrors the backend audio_url() / README pattern.
export const trackUrl = (trackId: string | number) =>
  `https://prod-1.storage.jamendo.com/download/track/${trackId}/mp32/`;

export const SAMPLE_TRACKS: SampleTrack[] = [
  { id: "161538", title: "Constellation", artist: "Reno Project", url: trackUrl("161538") },
  { id: "161536", title: "Afterwork", artist: "Reno Project", url: trackUrl("161536") },
  { id: "161537", title: "Atlanta", artist: "Reno Project", url: trackUrl("161537") },
  { id: "161539", title: "Down", artist: "Reno Project", url: trackUrl("161539") },
  // Occasionally throttled to 0 bytes — handy for testing the onError path.
  { id: "161535", title: "73rd Moon", artist: "Reno Project", url: trackUrl("161535") },
];
