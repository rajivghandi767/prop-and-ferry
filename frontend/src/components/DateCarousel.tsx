interface DateCarouselProps {
  selectedDate: Date;
  onDateSelect: (date: Date) => void;
  availableDates: string[]; // Array of 'YYYY-MM-DD' strings
}

export function DateCarousel({
  selectedDate,
  onDateSelect,
  availableDates,
}: DateCarouselProps) {
  // Safe local date formatting to avoid UTC timezone shifts
  const pad = (n: number) => n.toString().padStart(2, "0");
  const toISODate = (d: Date) =>
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  // Generate 7 days (3 before, today, 3 after)
  const dateWindow = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date(
      selectedDate.getFullYear(),
      selectedDate.getMonth(),
      selectedDate.getDate(),
    );
    d.setDate(d.getDate() + (i - 3));
    return d;
  });

  const daysOfWeek = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  const months = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
  ];

  return (
    <div className="flex items-center justify-between bg-white dark:bg-black border border-gray-200 dark:border-neutral-800 shadow-sm p-4 rounded-xl overflow-x-auto gap-2">
      {dateWindow.map((date) => {
        const dateStr = toISODate(date);
        const isSelected = toISODate(selectedDate) === dateStr;
        const hasTravel = availableDates.includes(dateStr);

        return (
          <button
            key={dateStr}
            onClick={() => onDateSelect(date)}
            disabled={!hasTravel}
            className={`
              flex flex-col items-center justify-center p-3 rounded-lg min-w-17.5 transition-all shrink-0 relative overflow-hidden
              ${isSelected ? "bg-blue-600 text-white shadow-md border border-blue-600" : "text-gray-600 dark:text-neutral-300 hover:bg-gray-100 dark:hover:bg-neutral-900 border border-transparent"}
              ${!hasTravel && !isSelected ? "opacity-30 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            <span className="text-[10px] font-bold tracking-widest">
              {daysOfWeek[date.getDay()]}
            </span>
            <span className="text-2xl font-black my-0.5">{date.getDate()}</span>
            <span className="text-[10px] font-bold uppercase tracking-widest">
              {months[date.getMonth()]}
            </span>

            {/* Indicator Dot */}
            <div
              className={`w-1.5 h-1.5 rounded-full mt-1.5 transition-colors duration-300 ${hasTravel && !isSelected ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-transparent"}`}
            ></div>
          </button>
        );
      })}
    </div>
  );
}
