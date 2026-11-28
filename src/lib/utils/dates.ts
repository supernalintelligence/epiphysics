const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

type DateStyle = 'long' | 'short' | 'compact' | 'month';

/**
 * Publication dates use the UTC calendar on both server and client.
 * Date-only inputs retain their stated day; ISO timestamps with an offset are
 * converted to UTC. An ISO timestamp without an offset is interpreted as UTC.
 * Date objects from the filesystem frontmatter loader are UTC instants too.
 * Missing values are empty; invalid or unsupported strings remain unchanged.
 */
export function formatDate(dateString: string | Date | null | undefined, style: DateStyle = 'long'): string {
  if (dateString instanceof Date) {
    return Number.isFinite(dateString.getTime()) ? formatUTCDate(dateString, style) : 'Invalid Date';
  }
  if (typeof dateString !== 'string' || !dateString) return '';
  const match = dateString.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2})(\.\d{1,9})?)?(Z|[+-]\d{2}:\d{2})?)?$/);
  if (!match) return dateString;

  const [, year, month, day, hour, minute, second, fraction, offset] = match;
  const calendar = new Date(`${year}-${month}-${day}T00:00:00.000Z`);
  // Date parsing can normalize February 30, so validate the stated calendar day.
  if (!Number.isFinite(calendar.getTime()) || calendar.getUTCFullYear() !== Number(year)
      || calendar.getUTCMonth() + 1 !== Number(month) || calendar.getUTCDate() !== Number(day)) return dateString;
  if (hour !== undefined && (Number(hour) > 23 || Number(minute) > 59 || Number(second || 0) > 59)) return dateString;

  const timestamp = hour === undefined ? calendar : new Date(
    `${year}-${month}-${day}T${hour}:${minute}:${second || '00'}${fraction ? fraction.slice(0, 4).padEnd(4, '0') : '.000'}${offset || 'Z'}`
  );
  if (!Number.isFinite(timestamp.getTime())) return dateString;

  return formatUTCDate(timestamp, style);
}

function formatUTCDate(timestamp: Date, style: DateStyle): string {
  const monthName = MONTHS[timestamp.getUTCMonth()];
  const date = timestamp.getUTCDate();
  const fullYear = timestamp.getUTCFullYear();
  if (style === 'month') return `${monthName} ${fullYear}`;
  if (style === 'compact') return `${monthName.slice(0, 3)} ${date}`;
  return `${style === 'short' ? monthName.slice(0, 3) : monthName} ${date}, ${fullYear}`;
}
