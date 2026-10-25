// Local calendar date (YYYY-MM-DD). toISOString() is UTC and returns
// yesterday's date between 00:00 and 01:00 in Lagos.
export function localDateString(date: Date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}
