/**
 * Examples (assuming the device's local time zone):
 * formatDumpTime('2026-10-12T22:42:00', new Date(2026, 9, 12, 23, 0)) -> Today · 10:42 PM
 * formatDumpTime('2026-10-11T18:12:00', new Date(2026, 9, 12, 23, 0)) -> Yesterday · 6:12 PM
 * formatDumpTime('2026-10-12T15:45:00', new Date(2026, 9, 14, 9, 0)) -> 12 Oct · 3:45 PM
 * formatDumpTime('2026-01-03T08:05:00', new Date(2026, 10, 1, 9, 0)) -> 3 Jan · 8:05 AM
 */
export function formatDumpTime(iso: string, now = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';

  const startOfDay = (value: Date) =>
    Date.UTC(value.getFullYear(), value.getMonth(), value.getDate());
  const dayDifference = (startOfDay(now) - startOfDay(date)) / 86_400_000;
  const time = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  if (dayDifference === 0) return `Today · ${time}`;
  if (dayDifference === 1) return `Yesterday · ${time}`;

  const day = date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  return `${day} · ${time}`;
}
