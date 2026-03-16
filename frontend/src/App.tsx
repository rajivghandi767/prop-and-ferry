import { useState, useEffect, useRef } from "react";
import type { Itinerary, ApiLeg, ApiResponse } from "./types";
import { useTheme } from "./hooks/useTheme";

// --- IMPORTED COMPONENTS ---
import { AirportSelect } from "./components/AirportSelect";
import { ProjectSwitcher } from "./components/ProjectSwitcher";
import { ReportModal } from "./components/ReportModal";
import { DateCarousel } from "./components/DateCarousel";
import { LeanCalendar } from "./components/LeanCalendar";
import { API_URL } from "./config";

// ==========================================
// 1. DATE & TIME FORMATTING HELPERS
// ==========================================
// These helpers ensure consistent, local-timezone rendering
// without relying on heavy external libraries like moment.js

const getTodayString = () => {
  const pad = (n: number) => n.toString().padStart(2, "0");
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const parseDateLocal = (dateStr: string) => {
  if (!dateStr) return new Date();
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
};

const formatDateShort = (dateStr?: string) => {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
};

const formatTime = (timeStr?: string) => {
  if (!timeStr) return "";
  const parts = timeStr.split(":");
  if (parts.length < 2) return timeStr;
  const date = new Date();
  date.setHours(parseInt(parts[0]), parseInt(parts[1]));
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
};

const formatDuration = (minutes: number | null) => {
  if (!minutes) return "--";
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
};

const formatSchedule = (days?: string) => {
  if (!days) return "";
  if (days.includes("1234567")) return "Runs Daily";
  if (days === "12345") return "Runs Mon-Fri";
  const map: Record<string, string> = {
    "1": "Mon",
    "2": "Tue",
    "3": "Wed",
    "4": "Thu",
    "5": "Fri",
    "6": "Sat",
    "7": "Sun",
  };
  return (
    "Runs " +
    days
      .split("")
      .map((d) => map[d])
      .join(", ")
  );
};

// ==========================================
// 2. MAIN APPLICATION COMPONENT
// ==========================================
function App() {
  const { theme, toggleTheme } = useTheme();

  // --- Search Parameters State ---
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState(getTodayString());

  // --- UI/UX & Availability State ---
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const calendarRef = useRef<HTMLDivElement>(null);

  // --- API Results State ---
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [displayDate, setDisplayDate] = useState(""); // The date actually shown in the results
  const [dateChanged, setDateChanged] = useState(false); // Flags if the backend auto-shifted the user's date
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ==========================================
  // 3. LIFECYCLE EFFECTS
  // ==========================================

  // EFFECT: Fetch route availability when airports are selected
  // This powers the green dots on the Calendar and Carousel
  useEffect(() => {
    if (origin.length >= 3 && destination.length >= 3) {
      fetch(
        `${API_URL}/api/routes/available-dates/?origin=${origin}&destination=${destination}`,
      )
        .then((res) => res.json())
        .then((data) => {
          if (data.available_dates) setAvailableDates(data.available_dates);
        })
        .catch(console.error);
    } else {
      setAvailableDates([]); // Reset if airports are cleared
    }
  }, [origin, destination]);

  // EFFECT: Close the calendar popover if the user clicks outside of it
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        calendarRef.current &&
        !calendarRef.current.contains(event.target as Node)
      ) {
        setIsCalendarOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // ==========================================
  // 4. EVENT HANDLERS
  // ==========================================

  const handleSwap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  // The core function that triggers the Django backend search
  const performSearch = async (searchDate: string) => {
    setLoading(true);
    setError("");
    setItineraries([]);
    setDateChanged(false);
    setDisplayDate(searchDate);

    try {
      const params = new URLSearchParams({
        origin,
        destination,
        date: searchDate,
      });
      const response = await fetch(`${API_URL}/api/routes/search/?${params}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch routes");
      }

      const data: ApiResponse = await response.json();

      // Check if the backend implemented fallback logic (shifting to the next valid date)
      if (data.date_was_changed) {
        setDateChanged(true);
        setDisplayDate(data.found_date);
        setDate(data.found_date); // Sync UI state with the backend's forced change
      } else {
        setDisplayDate(data.found_date || searchDate);
      }

      setItineraries(data.results);
      if (data.results.length === 0) {
        setError(
          `No routes found from ${origin} to ${destination} within the next 3 days.`,
        );
      }
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  // Wrapper for the main "Find Routes" button
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsCalendarOpen(false);
    performSearch(date);
  };

  // Triggered when a user clicks a date on EITHER the Carousel or the Calendar
  const handleDateSelect = (selectedDate: Date) => {
    const pad = (n: number) => n.toString().padStart(2, "0");
    const dateStr = `${selectedDate.getFullYear()}-${pad(selectedDate.getMonth() + 1)}-${pad(selectedDate.getDate())}`;

    setDate(dateStr);
    setIsCalendarOpen(false);

    // Auto-trigger search if we already have origin/destination (UX enhancement)
    if (origin && destination) {
      performSearch(dateStr);
    }
  };

  // ==========================================
  // 5. RENDER
  // ==========================================
  return (
    <div className="min-h-screen bg-white dark:bg-black flex flex-col font-sans text-neutral-900 dark:text-white transition-colors duration-200">
      {/* HEADER */}
      <header className="bg-white dark:bg-black border-b border-gray-200 dark:border-neutral-800 py-3 sticky top-0 z-50">
        <div className="container mx-auto px-4 flex items-center justify-between min-h-12">
          <div className="flex items-center justify-start w-24">
            <ProjectSwitcher align="left" />
          </div>
          <div className="text-center flex-1 flex justify-center items-center gap-2">
            <span className="text-2xl">✈️⛴️</span>
            <h1 className="text-xl font-bold text-blue-600 dark:text-blue-400">
              Prop & Ferry
            </h1>
          </div>
          <div className="flex items-center justify-end w-24">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-black dark:text-white hover:bg-gray-100 dark:hover:bg-neutral-900 transition-colors"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
          </div>
        </div>
      </header>

      <main className="grow container mx-auto px-4 py-8 flex flex-col items-center">
        {/* HERO SECTION (Hidden when results exist) */}
        {!itineraries.length && !loading && (
          <div className="text-center mb-10 mt-10">
            <h2 className="text-4xl font-extrabold mb-4 text-black dark:text-white">
              Unlock the{" "}
              <span className="text-blue-600 dark:text-blue-400">
                Hidden Caribbean
              </span>
            </h2>
            <p className="text-neutral-600 dark:text-neutral-400">
              Connect major flights with local island hoppers and ferries.
            </p>
          </div>
        )}

        {/* --- SEARCH BOX CONTROL CENTER --- */}
        <div className="bg-white dark:bg-black p-6 rounded-xl shadow-md w-full max-w-4xl border border-gray-200 dark:border-neutral-800 mb-8">
          <div className="flex flex-col md:flex-row gap-4 items-center md:items-end">
            <div className="w-full md:flex-1">
              <AirportSelect
                label="From"
                placeholder="JFK..."
                value={origin}
                onChange={setOrigin}
              />
            </div>

            <button
              onClick={handleSwap}
              className="p-3 rounded-full bg-gray-100 dark:bg-neutral-900 hover:bg-gray-200 dark:hover:bg-neutral-800 text-blue-600 transition-colors transform md:rotate-90"
            >
              ⇅
            </button>

            <div className="w-full md:flex-1">
              <AirportSelect
                label="To"
                placeholder="DOM..."
                value={destination}
                onChange={setDestination}
              />
            </div>

            {/* CUSTOM DATE PICKER LOGIC */}
            <div className="w-full md:flex-1 relative" ref={calendarRef}>
              <label className="text-xs font-semibold text-neutral-500 uppercase mb-1 block">
                Date
              </label>

              {/* Trigger button that replaces the native HTML <input type="date"> */}
              <button
                onClick={() => setIsCalendarOpen(!isCalendarOpen)}
                className="w-full p-3 text-left font-medium bg-white dark:bg-black text-black dark:text-white rounded-lg border border-gray-300 dark:border-neutral-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              >
                {formatDateShort(date)}
              </button>

              {/* The Floating Calendar Popover */}
              {isCalendarOpen && (
                <div className="absolute top-full right-0 mt-2 z-50 animate-fade-in-down">
                  <LeanCalendar
                    selectedDate={parseDateLocal(date)}
                    onDateSelect={handleDateSelect}
                    availableDates={availableDates}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 flex justify-center">
            <button
              onClick={handleSearchSubmit}
              disabled={loading}
              className="w-full md:w-1/3 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 transition-colors shadow-md"
            >
              {loading ? "Searching..." : "Find Routes"}
            </button>
          </div>
        </div>

        {/* --- RESULTS AREA --- */}
        <div className="w-full max-w-3xl space-y-4 mb-20">
          {/* THE DATE CAROUSEL (Appears above results for rapid date switching) */}
          {(itineraries.length > 0 || dateChanged) && (
            <div className="mb-6 animate-fade-in-up">
              <DateCarousel
                selectedDate={parseDateLocal(displayDate)}
                onDateSelect={handleDateSelect}
                availableDates={availableDates}
              />
            </div>
          )}

          {/* ALERTS */}
          {dateChanged && (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 rounded-lg border border-yellow-200 dark:border-yellow-700 text-center text-sm mb-4">
              ⚠️ No trips found on {parseDateLocal(date).toLocaleDateString()}.
              Moved to next available date.
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800 text-center">
              {error}
            </div>
          )}

          {/* ITINERARY CARDS */}
          {itineraries.map((itinerary) => (
            <div
              key={itinerary.id}
              className="bg-white dark:bg-black p-6 rounded-lg shadow-sm border border-gray-200 dark:border-neutral-800 hover:shadow-md transition-all"
            >
              {itinerary.legs.map((leg: ApiLeg, i: number) => (
                <div key={i}>
                  {/* Connection Indicator */}
                  {i > 0 && (
                    <div className="my-4 pl-4 border-l-2 border-dashed border-gray-300 dark:border-neutral-700 ml-3">
                      <div className="text-xs font-bold text-neutral-500 uppercase tracking-wide">
                        {itinerary.legs[i - 1].layover_text || "Connection"}
                      </div>
                    </div>
                  )}

                  <div className={`${i > 0 ? "pt-2" : ""}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        {/* Route Origin -> Destination */}
                        <div className="flex flex-col">
                          <div className="text-lg font-bold text-black dark:text-white flex items-center gap-2">
                            <span>{leg.origin.city || leg.origin.code}</span>
                            <span className="text-neutral-400 text-sm">➜</span>
                            <span>
                              {leg.destination.city || leg.destination.code}
                            </span>
                          </div>
                          <div className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">
                            {leg.origin.name} to {leg.destination.name}
                          </div>
                        </div>

                        {/* Times & Dates */}
                        <div className="text-neutral-700 dark:text-neutral-300 font-medium text-sm mt-1 flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-black dark:text-white">
                              {formatDateShort(leg.departure_date)}
                            </span>
                            <span>{formatTime(leg.departure_time)}</span>
                          </div>
                          <span className="hidden sm:inline text-neutral-400">
                            →
                          </span>
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-black dark:text-white">
                              {formatDateShort(leg.arrival_date)}
                            </span>
                            <span>{formatTime(leg.arrival_time)}</span>
                          </div>
                        </div>

                        {/* Carrier & Modality Tags */}
                        <div className="flex items-center gap-2 mt-2">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${leg.is_ferry ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300" : "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"}`}
                          >
                            {leg.is_ferry ? "Ferry" : "Flight"}
                          </span>
                          <span className="text-neutral-500 dark:text-neutral-400 text-xs">
                            <span className="font-medium text-neutral-700 dark:text-neutral-300">
                              {leg.carrier.name}
                            </span>
                            {leg.flight_number
                              ? ` • ${leg.flight_number}`
                              : ` (${leg.carrier.code})`}
                            {leg.aircraft_type && ` • ${leg.aircraft_type}`}
                            {` • ${formatDuration(leg.duration_minutes)}`}
                          </span>
                        </div>

                        {/* Pricing & Scheduling Details */}
                        {leg.days_of_operation ? (
                          <div className="text-blue-500/80 dark:text-blue-400/80 text-xs italic mt-1">
                            {formatSchedule(leg.days_of_operation)}
                          </div>
                        ) : (
                          <div className="flex gap-2 items-center mt-1">
                            <span className="text-indigo-500/80 dark:text-indigo-400/80 text-xs italic">
                              Sailing confirmed
                            </span>
                            {leg.price_text && (
                              <span className="text-xs font-bold text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 rounded-full">
                                {leg.price_text}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Booking Link */}
                      <div className="text-right flex flex-col items-end gap-2">
                        {leg.carrier.website ? (
                          <a
                            href={leg.carrier.website}
                            target="_blank"
                            rel="noreferrer"
                            className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-4 py-2 rounded-full font-bold shadow-sm"
                          >
                            Book Direct
                          </a>
                        ) : (
                          <span className="bg-gray-100 dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 text-neutral-500 text-xs px-3 py-1 rounded-full">
                            Info Only
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </main>

      <footer className="bg-white dark:bg-black border-t border-gray-200 dark:border-neutral-800 py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center items-center gap-2 mb-4">
            <span className="text-xl">✈️⛴️</span>
            <span className="font-bold text-black dark:text-white">
              Prop & Ferry
            </span>
          </div>
          <div className="mb-4">
            <a
              href="mailto:dev@rajivwallace.com"
              className="text-blue-600 dark:text-blue-400 hover:underline text-sm font-medium transition-colors"
            >
              dev@rajivwallace.com
            </a>
          </div>
          <div className="text-xs text-neutral-500">
            &copy; {new Date().getFullYear()} Rajiv Wallace. All rights
            reserved.
          </div>
        </div>
      </footer>

      <ReportModal />
    </div>
  );
}

export default App;
