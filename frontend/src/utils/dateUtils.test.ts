import { describe, it, expect } from "vitest";
import {
  toISODate,
  getSlidingWindowEnd,
  isDateInSlidingWindow,
} from "./dateUtils";

describe("dateUtils - Sliding Window & Formatting", () => {
  it("formats Date to YYYY-MM-DD correctly", () => {
    const d = new Date(2026, 8, 19); // September 19, 2026
    expect(toISODate(d)).toBe("2026-09-19");
  });

  describe("Server-Driven Sliding Window Bounds", () => {
    it("respects explicit server windowStart and windowEnd when provided", () => {
      const wednesday = new Date(2026, 8, 16);
      const thursday = new Date(2026, 8, 17);
      const sunday = new Date(2026, 8, 20);
      const monday = new Date(2026, 8, 21);

      expect(
        isDateInSlidingWindow(wednesday, wednesday, "2026-09-17", "2026-09-20"),
      ).toBe(false);
      expect(
        isDateInSlidingWindow(thursday, wednesday, "2026-09-17", "2026-09-20"),
      ).toBe(true);
      expect(
        isDateInSlidingWindow(sunday, wednesday, "2026-09-17", "2026-09-20"),
      ).toBe(true);
      expect(
        isDateInSlidingWindow(monday, wednesday, "2026-09-17", "2026-09-20"),
      ).toBe(false);
    });
  });

  describe("Wednesday Cycle (Thu, Fri, Sat, Sun)", () => {
    // 2026-09-16 is a Wednesday (day 3)
    const wednesday = new Date(2026, 8, 16);

    it("calculates upcoming Sunday as the window end for Wednesday", () => {
      const windowEnd = getSlidingWindowEnd(wednesday);
      expect(toISODate(windowEnd)).toBe("2026-09-20"); // Sunday
    });

    it("enables Thursday, Friday, Saturday, and Sunday for Wednesday search", () => {
      const thursday = new Date(2026, 8, 17);
      const friday = new Date(2026, 8, 18);
      const saturday = new Date(2026, 8, 19);
      const sunday = new Date(2026, 8, 20);

      expect(isDateInSlidingWindow(thursday, wednesday)).toBe(true);
      expect(isDateInSlidingWindow(friday, wednesday)).toBe(true);
      expect(isDateInSlidingWindow(saturday, wednesday)).toBe(true);
      expect(isDateInSlidingWindow(sunday, wednesday)).toBe(true);
    });

    it("disables today (Wednesday), past dates, and dates beyond Sunday", () => {
      const past = new Date(2026, 8, 15);
      const monday = new Date(2026, 8, 21); // Beyond Sunday

      expect(isDateInSlidingWindow(wednesday, wednesday)).toBe(false); // Today
      expect(isDateInSlidingWindow(past, wednesday)).toBe(false); // Past
      expect(isDateInSlidingWindow(monday, wednesday)).toBe(false); // Beyond window
    });

    it("enables only remaining days when searching on Thursday", () => {
      const thursday = new Date(2026, 8, 17);
      const friday = new Date(2026, 8, 18);
      const saturday = new Date(2026, 8, 19);
      const sunday = new Date(2026, 8, 20);

      expect(isDateInSlidingWindow(thursday, thursday)).toBe(false); // Today disabled
      expect(isDateInSlidingWindow(friday, thursday)).toBe(true);
      expect(isDateInSlidingWindow(saturday, thursday)).toBe(true);
      expect(isDateInSlidingWindow(sunday, thursday)).toBe(true);
    });

    it("enables only Sunday when searching on Saturday", () => {
      const saturday = new Date(2026, 8, 19);
      const sunday = new Date(2026, 8, 20);
      const monday = new Date(2026, 8, 21);

      expect(isDateInSlidingWindow(saturday, saturday)).toBe(false); // Today disabled
      expect(isDateInSlidingWindow(sunday, saturday)).toBe(true);
      expect(isDateInSlidingWindow(monday, saturday)).toBe(false);
    });
  });

  describe("Sunday Cycle (Mon, Tue, Wed)", () => {
    // 2026-09-20 is a Sunday (day 0)
    const sunday = new Date(2026, 8, 20);

    it("calculates upcoming Wednesday as the window end for Sunday", () => {
      const windowEnd = getSlidingWindowEnd(sunday);
      expect(toISODate(windowEnd)).toBe("2026-09-23"); // Wednesday
    });

    it("enables Monday, Tuesday, and Wednesday for Sunday search", () => {
      const monday = new Date(2026, 8, 21);
      const tuesday = new Date(2026, 8, 22);
      const wednesday = new Date(2026, 8, 23);

      expect(isDateInSlidingWindow(sunday, sunday)).toBe(false); // Today disabled
      expect(isDateInSlidingWindow(monday, sunday)).toBe(true);
      expect(isDateInSlidingWindow(tuesday, sunday)).toBe(true);
      expect(isDateInSlidingWindow(wednesday, sunday)).toBe(true);
    });

    it("disables dates beyond Wednesday", () => {
      const nextThursday = new Date(2026, 8, 24);
      expect(isDateInSlidingWindow(nextThursday, sunday)).toBe(false);
    });
  });
});

