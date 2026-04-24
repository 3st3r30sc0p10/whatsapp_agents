const BUFFER_MS = 23 * 3600 * 1000;

export function isWithinSessionWindow(lastUserMessageAt: Date | null): boolean {
  if (!lastUserMessageAt) return false;
  return Date.now() - lastUserMessageAt.getTime() < BUFFER_MS;
}
