/**
 * Utility functions for sliding window calendar & date formatting.
 */

const pad = (n: number): string => n.toString().padStart(2, "0");

/**
 * Formats a Date to YYYY-MM-DD using local time components to prevent UTC date shifting.
 */
export const toISODate = (d: Date): string =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/**
 * Calculates the batch end date for the current bi-weekly scrape window
 * aligned with the Wednesday / Sunday automated scraper schedule:
 * - Wednesday Cycle (Wed, Thu, Fri, Sat): batch ends on upcoming Sunday (7 - day).
 * - Sunday Cycle (Sun, Mon, Tue): batch ends on upcoming Wednesday (3 - day).
 */
export const getSlidingWindowEnd = (today: Date = new Date()): Date => {
  const day = today.getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat
  // Wednesday (3), Thursday (4), Friday (5), Saturday (6): batch ends on upcoming Sunday (7 - day)
  // Sunday (0), Monday (1), Tuesday (2): batch ends on upcoming Wednesday (3 - day)
  const daysUntilEnd =
    day === 3 || day === 4 || day === 5 || day === 6 ? 7 - day : 3 - day;
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() + daysUntilEnd);
};

/**
 * Determines whether a date is clickable in the calendar:
 * - Uses server-provided `windowStart` and `windowEnd` (YYYY-MM-DD) when available.
 * - Otherwise falls back to the local Wed/Sun sliding window calculation:
 *   - Past dates (<= today): false
 *   - Dates within sliding window (today < date <= windowEnd): true
 *   - Dates beyond sliding window (> windowEnd): false
 */
export const isDateInSlidingWindow = (
  date: Date,
  today: Date = new Date(),
  windowStart?: string,
  windowEnd?: string,
): boolean => {
  if (windowStart && windowEnd) {
    const dateStr = toISODate(date);
    return dateStr >= windowStart && dateStr <= windowEnd;
  }
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const computedEnd = getSlidingWindowEnd(today);
  return d > t && d <= computedEnd;
};

