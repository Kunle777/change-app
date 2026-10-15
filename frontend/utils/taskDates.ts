export function isTaskOverdue(
  dueDate: string | null | undefined,
  status: string | null | undefined,
): boolean {
  if (!dueDate || !['pending', 'in_progress', '1', '2'].includes(status ?? '')) {
    return false;
  }

  const date = new Date(dueDate);
  if (!Number.isFinite(date.getTime())) return false;

  const now = new Date();
  return (
    date.getFullYear() < now.getFullYear() ||
    (date.getFullYear() === now.getFullYear() && date.getMonth() < now.getMonth()) ||
    (date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() < now.getDate())
  );
}
