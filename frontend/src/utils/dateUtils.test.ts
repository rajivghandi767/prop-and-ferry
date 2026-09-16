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

  describe("Wednesday Cycle (Option A: Thu, Fri, Sat)", () => {
    // 2026-09-16 is a Wednesday (day 3)
    const wednesday = new Date(2026, 8, 16);

    it("calculates Saturday as the window end for Wednesday", () => {
      const windowEnd = getSlidingWindowEnd(wednesday);
      expect(toISODate(windowEnd)).toBe("2026-09-19"); // Saturday
    });

    it("enables Thursday, Friday, and Saturday for Wednesday search", () => {
      const thursday = new Date(2026, 8, 17);
      const friday = new Date(2026, 8, 18);
      const saturday = new Date(2026, 8, 19);

      expect(isDateInSlidingWindow(thursday, wednesday)).toBe(true);
      expect(isDateInSlidingWindow(friday, wednesday)).toBe(true);
      expect(isDateInSlidingWindow(saturday, wednesday)).toBe(true);
    });

    it("disables today (Wednesday), past dates, and dates beyond Saturday", () => {
      const past = new Date(2026, 8, 15);
      const sunday = new Date(2026, 8, 20); // Beyond Saturday

      expect(isDateInSlidingWindow(wednesday, wednesday)).toBe(false); // Today
      expect(isDateInSlidingWindow(past, wednesday)).toBe(false); // Past
      expect(isDateInSlidingWindow(sunday, wednesday)).toBe(false); // Beyond window
    });

    it("enables only remaining days when searching on Thursday (mid-cycle Option A)", () => {
      const thursday = new Date(2026, 8, 17);
      const friday = new Date(2026, 8, 18);
      const saturday = new Date(2026, 8, 19);

      expect(isDateInSlidingWindow(thursday, thursday)).toBe(false); // Today disabled
      expect(isDateInSlidingWindow(friday, thursday)).toBe(true); // Remaining future day
      expect(isDateInSlidingWindow(saturday, thursday)).toBe(true); // Remaining future day
    });

    it("enables only Saturday when searching on Friday", () => {
      const friday = new Date(2026, 8, 18);
      const saturday = new Date(2026, 8, 19);
      const sunday = new Date(2026, 8, 20);

      expect(isDateInSlidingWindow(friday, friday)).toBe(false); // Today disabled
      expect(isDateInSlidingWindow(saturday, friday)).toBe(true); // Remaining future day
      expect(isDateInSlidingWindow(sunday, friday)).toBe(false); // Beyond window
    });
  });

  describe("Saturday Cycle (Option A: Sun, Mon, Tue, Wed)", () => {
    // 2026-09-19 is a Saturday (day 6)
    const saturday = new Date(2026, 8, 19);

    it("calculates upcoming Wednesday as the window end for Saturday", () => {
      const windowEnd = getSlidingWindowEnd(saturday);
      expect(toISODate(windowEnd)).toBe("2026-09-23"); // Wednesday
    });

    it("enables Sunday, Monday, Tuesday, and Wednesday for Saturday search", () => {
      const sunday = new Date(2026, 8, 20);
      const monday = new Date(2026, 8, 21);
      const tuesday = new Date(2026, 8, 22);
      const wednesday = new Date(2026, 8, 23);

      expect(isDateInSlidingWindow(sunday, saturday)).toBe(true);
      expect(isDateInSlidingWindow(monday, saturday)).toBe(true);
      expect(isDateInSlidingWindow(tuesday, saturday)).toBe(true);
      expect(isDateInSlidingWindow(wednesday, saturday)).toBe(true);
    });

    it("disables today (Saturday) and dates beyond Wednesday", () => {
      const nextThursday = new Date(2026, 8, 24);

      expect(isDateInSlidingWindow(saturday, saturday)).toBe(false); // Today
      expect(isDateInSlidingWindow(nextThursday, saturday)).toBe(false); // Beyond window
    });

    it("enables remaining days when searching on Sunday", () => {
      const sunday = new Date(2026, 8, 20);
      const monday = new Date(2026, 8, 21);
      const tuesday = new Date(2026, 8, 22);
      const wednesday = new Date(2026, 8, 23);

      expect(isDateInSlidingWindow(sunday, sunday)).toBe(false); // Today disabled
      expect(isDateInSlidingWindow(monday, sunday)).toBe(true);
      expect(isDateInSlidingWindow(tuesday, sunday)).toBe(true);
      expect(isDateInSlidingWindow(wednesday, sunday)).toBe(true);
    });
  });
});
