import { useState, useEffect, useRef } from "react";
import type { Itinerary, ApiLeg, ApiResponse } from "./types";
import { useThemeContext } from "./context/ThemeContext";
import { Sun, Moon, Plane, Ship, Users } from "lucide-react";

// --- IMPORTED COMPONENTS ---
import { AirportSelect } from "./components/AirportSelect";
import { ProjectSwitcher } from "./components/ProjectSwitcher";
import { ReportModal } from "./components/ReportModal";
import { DateCarousel } from "./components/DateCarousel";
import { LeanCalendar } from "./components/LeanCalendar";
import { API_URL } from "./config";

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

type FilterType = "all" | "ferry" | "flight";

function App() {
  const { theme, toggleTheme } = useThemeContext();

  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState(getTodayString());
  const [searchedDate, setSearchedDate] = useState("");

  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const calendarRef = useRef<HTMLDivElement>(null);

  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [filter, setFilter] = useState<FilterType>("all");
  const [displayDate, setDisplayDate] = useState("");
  const [dateChanged, setDateChanged] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      setAvailableDates([]);
    }
  }, [origin, destination]);

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

  const handleSwap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const performSearch = async (searchDate: string) => {
    setLoading(true);
    setError("");
    setItineraries([]);
    setDateChanged(false);
    setDisplayDate(searchDate);
    setSearchedDate(searchDate);
    setFilter("all"); // Reset filter on new search

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

      if (data.date_was_changed) {
        setDateChanged(true);
        setDisplayDate(data.found_date);
        setDate(data.found_date);
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

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsCalendarOpen(false);
    performSearch(date);
  };

  const handleDateSelect = (selectedDate: Date) => {
    const pad = (n: number) => n.toString().padStart(2, "0");
    const dateStr = `${selectedDate.getFullYear()}-${pad(selectedDate.getMonth() + 1)}-${pad(selectedDate.getDate())}`;

    setDate(dateStr);
    setIsCalendarOpen(false);

    if (origin && destination) performSearch(dateStr);
  };

  // --- FILTER & SORT LOGIC ---
  const displayedItineraries = itineraries
    .filter((itinerary) => {
      const hasFerry = itinerary.legs.some((leg) => leg.is_ferry);
      if (filter === "ferry") return hasFerry;
      if (filter === "flight") return !hasFerry;
      return true;
    })
    .sort((a, b) => {
      // Prioritize itineraries that include a ferry connection
      const aHasFerry = a.legs.some((leg) => leg.is_ferry) ? 1 : 0;
      const bHasFerry = b.legs.some((leg) => leg.is_ferry) ? 1 : 0;
      return bHasFerry - aHasFerry;
    });

  return (
    <div className="min-h-screen bg-bg-light dark:bg-bg-dark flex flex-col font-sans text-neutral-900 dark:text-white transition-colors duration-200">
      <header className="bg-bg-light dark:bg-bg-dark border-b border-gray-200 dark:border-neutral-800 py-3 sticky top-0 z-50 transition-colors duration-200">
        <div className="container mx-auto px-4 flex items-center justify-between min-h-12">
          <div className="flex items-center justify-start w-24">
            <ProjectSwitcher align="left" />
          </div>
          <div className="text-center flex-1 flex justify-center items-center gap-2">
            <div className="flex -space-x-1 text-black dark:text-white">
              <Plane size={24} />
              <Ship size={24} />
            </div>
            <h1 className="text-xl font-bold text-black dark:text-white">
              Prop & Ferry
            </h1>
          </div>
          <div className="flex items-center justify-end w-24">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-neutral-600 dark:text-neutral-400 hover:bg-gray-100 dark:hover:bg-neutral-900 transition-colors"
            >
              {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>
      </header>

      <main className="grow container mx-auto px-4 py-8 flex flex-col items-center">
        {!itineraries.length && !loading && (
          <div className="text-center mb-10 mt-10">
            <h2 className="text-4xl font-extrabold mb-4 text-black dark:text-white">
              Unlock the{" "}
              <span className="text-brand-light dark:text-brand-dark">
                Hidden Caribbean
              </span>
            </h2>
            <p className="text-neutral-600 dark:text-neutral-400">
              Connect major flights with local island hoppers and ferries.
            </p>
          </div>
        )}

        <div className="bg-bg-light dark:bg-bg-dark p-6 rounded-xl shadow-md w-full max-w-4xl border border-gray-200 dark:border-neutral-800 mb-4 transition-colors duration-200">
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
              className="p-3 rounded-full bg-gray-100 dark:bg-neutral-900 hover:bg-gray-200 dark:hover:bg-neutral-800 text-brand-light dark:text-brand-dark transition-colors transform md:rotate-90"
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

            <div className="w-full md:flex-1 relative" ref={calendarRef}>
              <label className="text-xs font-semibold text-neutral-500 uppercase mb-1 block">
                Date
              </label>
              <button
                onClick={() => setIsCalendarOpen(!isCalendarOpen)}
                className="w-full p-3 text-left font-medium bg-bg-light dark:bg-bg-dark text-black dark:text-white rounded-lg border border-gray-300 dark:border-neutral-700 focus:border-brand-light dark:focus:border-brand-dark focus:ring-1 focus:ring-brand-light dark:focus:ring-brand-dark transition-colors"
              >
                {formatDateShort(date)}
              </button>

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
              className="w-full md:w-1/3 bg-brand-light dark:bg-brand-dark text-white dark:text-black hover:opacity-90 font-bold py-3 px-6 rounded-lg disabled:opacity-50 transition-colors shadow-md"
            >
              {loading ? "Searching..." : "Find Routes"}
            </button>
          </div>
        </div>

        {/* POC Disclaimer */}
        <div className="w-full max-w-4xl mb-8 px-4 animate-fade-in">
          <p className="text-xs text-neutral-500 dark:text-neutral-400 bg-gray-50 dark:bg-neutral-900/40 border border-gray-200 dark:border-neutral-800 rounded-lg p-3">
            <strong>⚠️ Proof of Concept Notice:</strong> Live flight schedules
            and pricing are actively indexed for a{" "}
            <strong>3-day rolling forecast</strong>. To optimize API usage, this
            platform is strictly scoped to routes terminating in{" "}
            <strong>Dominica (DOM)</strong>, originating from gateways in{" "}
            <strong>New York (NYC)</strong>, <strong>London (LON)</strong>, and{" "}
            <strong>Paris (PAR)</strong>.
          </p>
        </div>

        <div className="w-full max-w-3xl space-y-4 mb-20">
          {(itineraries.length > 0 || dateChanged) && (
            <div className="mb-6 animate-fade-in-up">
              <DateCarousel
                selectedDate={parseDateLocal(displayDate)}
                onDateSelect={handleDateSelect}
                availableDates={availableDates}
              />
            </div>
          )}

          {/* Segmented Filter Control */}
          {itineraries.length > 0 && (
            <div className="flex justify-center gap-2 mb-6 animate-fade-in">
              {(["all", "ferry", "flight"] as FilterType[]).map((type) => (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`px-4 py-2 rounded-full text-xs sm:text-sm font-semibold transition-colors ${
                    filter === type
                      ? "bg-brand-light dark:bg-brand-dark text-white dark:text-black shadow-sm"
                      : "bg-gray-100 dark:bg-neutral-900 text-neutral-600 dark:text-neutral-400 hover:bg-gray-200 dark:hover:bg-neutral-800"
                  }`}
                >
                  {type === "all" && "All Routes"}
                  {type === "ferry" && "Includes Ferry"}
                  {type === "flight" && "Flights Only"}
                </button>
              ))}
            </div>
          )}

          {dateChanged && searchedDate && (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 rounded-lg border border-yellow-200 dark:border-yellow-700 text-center text-sm mb-4">
              ⚠️ No trips found on{" "}
              {parseDateLocal(searchedDate).toLocaleDateString()}. Moved to next
              available date.
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800 text-center">
              {error}
            </div>
          )}

          {displayedItineraries.map((itinerary) => (
            <div
              key={itinerary.id}
              className="bg-bg-light dark:bg-bg-dark p-6 rounded-lg shadow-sm border border-gray-200 dark:border-neutral-800 hover:shadow-md transition-all animate-fade-in-up"
            >
              {itinerary.legs.map((leg: ApiLeg, i: number) => (
                <div key={i}>
                  {i > 0 && (
                    <div className="my-4 pl-4 border-l-2 border-dashed border-gray-300 dark:border-neutral-700 ml-3">
                      <div className="text-xs font-bold text-neutral-500 uppercase tracking-wide">
                        {itinerary.legs[i - 1].layover_text || "Connection"}
                      </div>
                    </div>
                  )}

                  <div className={`${i > 0 ? "pt-2" : ""}`}>
                    <div className="flex justify-between items-start">
                      <div className="flex-1 pr-4">
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

                        {/* 1. Scannable Carrier & Flight Info */}
                        <div className="flex items-center flex-wrap gap-2 mt-2.5">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider flex items-center gap-1 ${
                              leg.is_ferry
                                ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
                                : "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
                            }`}
                          >
                            {leg.is_ferry ? "⛴ Ferry" : "✈ Flight"}
                          </span>

                          <span className="text-neutral-500 dark:text-neutral-400 text-xs flex flex-wrap items-center gap-1.5">
                            <span
                              className={`font-bold ${
                                leg.is_ferry
                                  ? "text-indigo-700 dark:text-indigo-400"
                                  : "text-sky-700 dark:text-sky-400"
                              }`}
                            >
                              {leg.carrier.name}
                            </span>
                            <span className="opacity-40">•</span>
                            <span>
                              {leg.flight_number
                                ? leg.flight_number
                                : leg.carrier.code}
                            </span>
                            {leg.aircraft_type && (
                              <>
                                <span className="opacity-40">•</span>
                                <span>{leg.aircraft_type}</span>
                              </>
                            )}
                            <span className="opacity-40">•</span>
                            <span>{formatDuration(leg.duration_minutes)}</span>
                          </span>
                        </div>

                        {/* 2. Unified "Last Seen" Estimates Block */}
                        <div className="mt-3.5 pt-3 border-t border-gray-100 dark:border-neutral-800/50 flex flex-col gap-2">
                          <div className="text-[10px] font-bold text-neutral-400 dark:text-neutral-500 uppercase tracking-widest">
                            Price & Availability Last Seen
                          </div>

                          <div className="flex flex-wrap items-center gap-2">
                            {/* Price Pill */}
                            {leg.price_text ? (
                              <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/30 px-2.5 py-1 rounded-md border border-emerald-200/50 dark:border-emerald-800/30">
                                {leg.price_text}
                              </span>
                            ) : (
                              <span className="text-xs font-medium text-neutral-500 bg-gray-50 dark:bg-neutral-800 px-2.5 py-1 rounded-md border border-gray-200 dark:border-neutral-700">
                                Check Site
                              </span>
                            )}

                            {/* Seats Pill */}
                            <div
                              className={`flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-md border ${
                                leg.is_ferry
                                  ? "bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-300 dark:border-indigo-800/30"
                                  : "bg-amber-50 text-amber-700 border-amber-100 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800/30"
                              }`}
                            >
                              <Users
                                size={14}
                                className={leg.is_ferry ? "opacity-70" : ""}
                              />
                              <span>
                                {leg.is_ferry
                                  ? "General Seating"
                                  : `${leg.available_seats !== undefined && leg.available_seats !== null ? leg.available_seats : "--"} Seats Left`}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="text-right flex flex-col items-end gap-2">
                        {leg.carrier.website ? (
                          <a
                            href={leg.carrier.website}
                            target="_blank"
                            rel="noreferrer"
                            className="bg-brand-light dark:bg-brand-dark hover:opacity-90 text-white dark:text-black text-xs px-4 py-2 rounded-full font-bold shadow-sm"
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
          {displayedItineraries.length === 0 && itineraries.length > 0 && (
            <div className="text-center py-10 text-neutral-500">
              No routes match the selected filter.
            </div>
          )}
        </div>
      </main>

      <footer className="bg-bg-light dark:bg-bg-dark border-t border-gray-200 dark:border-neutral-800 py-8 transition-colors duration-200">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center items-center gap-2 mb-4">
            <div className="flex -space-x-1 text-neutral-700 dark:text-neutral-300">
              <Plane size={20} />
              <Ship size={20} />
            </div>
            <span className="font-bold text-black dark:text-white">
              Prop & Ferry
            </span>
          </div>
          <div className="mb-4">
            <a
              href="mailto:dev@rajivwallace.com"
              className="text-brand-light dark:text-brand-dark hover:underline text-sm font-medium transition-colors"
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
