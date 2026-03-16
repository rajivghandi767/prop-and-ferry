import { useState } from "react";

interface CalendarProps {
  selectedDate: Date;
  onDateSelect: (date: Date) => void;
  availableDates: string[];
}

export function LeanCalendar({
  selectedDate,
  onDateSelect,
  availableDates,
}: CalendarProps) {
  const [currentMonthView, setCurrentMonthView] = useState(
    new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1),
  );

  const pad = (n: number) => n.toString().padStart(2, "0");
  const toISODate = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  // Calendar Math
  const year = currentMonthView.getFullYear();
  const month = currentMonthView.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayOfMonth = new Date(year, month, 1).getDay(); // 0 = Sunday

  const prevMonth = () => setCurrentMonthView(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentMonthView(new Date(year, month + 1, 1));

  const daysOfWeek = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  return (
    <div className="w-full min-w-75 bg-white dark:bg-black rounded-xl border border-gray-200 dark:border-neutral-800 shadow-2xl p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4 text-black dark:text-white">
        <button
          type="button"
          onClick={prevMonth}
          className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-900 rounded-full font-bold transition-colors"
        >
          &lt;
        </button>
        <span className="font-bold text-lg tracking-wide">
          {currentMonthView.toLocaleString("default", {
            month: "long",
            year: "numeric",
          })}
        </span>
        <button
          type="button"
          onClick={nextMonth}
          className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-900 rounded-full font-bold transition-colors"
        >
          &gt;
        </button>
      </div>

      {/* Days of Week Row */}
      <div className="grid grid-cols-7 gap-1 text-center mb-2">
        {daysOfWeek.map((day) => (
          <div
            key={day}
            className="text-xs font-bold text-neutral-400 uppercase tracking-wider"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: firstDayOfMonth }).map((_, i) => (
          <div key={`empty-${i}`} className="p-2"></div>
        ))}

        {Array.from({ length: daysInMonth }).map((_, i) => {
          const date = new Date(year, month, i + 1);
          const dateStr = toISODate(date);
          const isSelected = toISODate(selectedDate) === dateStr;
          const hasTravel = availableDates.includes(dateStr);
          const isToday = toISODate(new Date()) === dateStr;

          return (
            <button
              key={i}
              type="button"
              onClick={() => {
                onDateSelect(date);
              }}
              disabled={!hasTravel}
              className={`
                p-2 rounded-full w-9 h-9 flex flex-col items-center justify-center text-sm mx-auto transition-all font-medium
                ${isSelected ? "bg-blue-600 text-white font-bold shadow-md" : "text-neutral-700 dark:text-neutral-300"}
                ${!isSelected && hasTravel ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/50" : ""}
                ${!hasTravel && !isSelected ? "opacity-20 cursor-not-allowed" : ""}
                ${isToday && !isSelected ? "border border-blue-500" : ""}
              `}
            >
              {i + 1}
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-5 pt-3 border-t border-gray-100 dark:border-neutral-900 flex items-center justify-center gap-6 text-xs text-neutral-500 dark:text-neutral-400 font-medium tracking-wide">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 bg-green-400 dark:bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>{" "}
          Active Routes
        </div>
      </div>
    </div>
  );
}
