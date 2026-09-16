/**
 * Utility functions for sliding window calendar & date formatting.
 */

const pad = (n: number) => n.toString().padStart(2, "0");

/**
 * Formats a Date to YYYY-MM-DD using local time components to prevent UTC date shifting.
 */
export const toISODate = (d: Date): string =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/**
 * Calculates the batch end date for the current bi-weekly scrape window:
 * - Wednesday Cycle (Wed, Thu, Fri): batch ends on upcoming Saturday (6).
 * - Saturday Cycle (Sat, Sun, Mon, Tue): batch ends on upcoming Wednesday (3).
 */
export const getSlidingWindowEnd = (today: Date = new Date()): Date => {
  const day = today.getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat
  let daysUntilEnd = 0;
  if (day === 3 || day === 4 || day === 5) {
    // Wednesday (3), Thursday (4), Friday (5): batch ends on upcoming Saturday (6)
    daysUntilEnd = 6 - day;
  } else if (day === 6) {
    // Saturday (6): batch ends on upcoming Wednesday (+4 days)
    daysUntilEnd = 4;
  } else {
    // Sunday (0), Monday (1), Tuesday (2): batch ends on upcoming Wednesday (3 - day)
    daysUntilEnd = 3 - day;
  }
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() + daysUntilEnd);
};

/**
 * Determines whether a date is clickable in the calendar:
 * - Past dates (< today): false
 * - Today: false (current day is disabled per user rules)
 * - Dates within sliding window (today < date <= windowEnd): true
 * - Dates beyond sliding window (> windowEnd): false
 */
export const isDateInSlidingWindow = (
  date: Date,
  today: Date = new Date()
): boolean => {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const windowEnd = getSlidingWindowEnd(today);
  return d > t && d <= windowEnd;
};
