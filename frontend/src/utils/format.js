export function formatDuration(totalSeconds) {
  const value = Number(totalSeconds);
  if (!Number.isFinite(value) || value <= 0) {
    return "0:00";
  }

  const seconds = Math.floor(value);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remaining = seconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}
