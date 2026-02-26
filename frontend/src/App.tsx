import { useState } from "react";
import { Sun, Moon } from "lucide-react";
import type { Itinerary, ApiLeg, ApiResponse } from "./types";
import { useTheme } from "./hooks/useTheme";
import { AirportSelect } from "./components/AirportSelect";
import { ProjectSwitcher } from "./components/ProjectSwitcher";
import { API_URL } from "./config";

// --- HELPERS ---
const getTodayString = () => {
  const d = new Date();
  const offset = d.getTimezoneOffset();
  const localDate = new Date(d.getTime() - offset * 60 * 1000);
  return localDate.toISOString().split("T")[0];
};

const parseDateLocal = (dateStr: string) => {
  if (!dateStr) return new Date();
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
};

const formatTime = (timeStr?: string) => {
  if (!timeStr) return "";
  const parts = timeStr.split(":");
  if (parts.length < 2) return timeStr;
  const hours = parseInt(parts[0]);
  const minutes = parseInt(parts[1]);
  const date = new Date();
  date.setHours(hours);
  date.setMinutes(minutes);
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
};

const formatDuration = (minutes: number | null) => {
  if (!minutes) return "--";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
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

// --- MAIN COMPONENT ---

function App() {
  const { theme, toggleTheme } = useTheme();

  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState(getTodayString());

  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [displayDate, setDisplayDate] = useState("");
  const [dateChanged, setDateChanged] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSwap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setItineraries([]);
    setDateChanged(false);
    setDisplayDate(date);

    try {
      const params = new URLSearchParams({ origin, destination, date });
      const response = await fetch(`${API_URL}/api/routes/search/?${params}`);

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error("Server Error: Check backend logs.");
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch routes");
      }

      const data: ApiResponse = await response.json();

      if (data.date_was_changed) {
        setDateChanged(true);
        setDisplayDate(data.found_date);
      } else {
        setDisplayDate(data.found_date || date);
      }

      setItineraries(data.results);

      if (data.results.length === 0) {
        setError(
          `No routes found from ${origin} to ${destination} within the next 3 days.`,
        );
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white dark:bg-black flex flex-col font-sans text-neutral-900 dark:text-white transition-colors duration-200">
      {/* 1. Solid, Symmetrical AMOLED Header */}
      <header className="bg-white dark:bg-black border-b border-gray-200 dark:border-neutral-800 py-3 sticky top-0 z-50">
        <div className="container mx-auto px-4 flex items-center justify-between min-h-[48px]">
          {/* LEFT: Project Switcher */}
          <div className="flex items-center justify-start w-24">
            <ProjectSwitcher align="left" />
          </div>

          {/* CENTER: Title (Retained blue branding, but mathematically centered) */}
          <div className="text-center flex-1 flex justify-center items-center gap-2">
            <span className="text-2xl">✈️⛴️</span>
            <h1 className="text-xl font-bold text-blue-600 dark:text-blue-400">
              Prop & Ferry
            </h1>
          </div>

          {/* RIGHT: Theme Toggle */}
          <div className="flex items-center justify-end w-24">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-black dark:text-white hover:bg-gray-100 dark:hover:bg-neutral-900 transition-colors"
            >
              {theme === "dark" ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="5"></circle>
                  <line x1="12" y1="1" x2="12" y2="3"></line>
                  <line x1="12" y1="21" x2="12" y2="23"></line>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                  <line x1="1" y1="12" x2="3" y2="12"></line>
                  <line x1="21" y1="12" x2="23" y2="12"></line>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="flex-grow container mx-auto px-4 py-8 flex flex-col items-center">
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

        {/* 2. AMOLED Search Box */}
        <div className="bg-white dark:bg-black p-6 rounded-xl shadow-md w-full max-w-4xl border-2 border-gray-200 dark:border-neutral-800 mb-8">
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
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M7 16V4M7 4L3 8M7 4L11 8" />
                <path d="M17 8v12M17 20l4-4M17 20l-4-4" />
              </svg>
            </button>
            <div className="w-full md:flex-1">
              <AirportSelect
                label="To"
                placeholder="DOM..."
                value={destination}
                onChange={setDestination}
              />
            </div>
            <div className="w-full md:flex-1">
              <label className="text-xs font-semibold text-neutral-500 uppercase mb-1">
                Date
              </label>
              {/* 3. Forced White Input */}
              <input
                type="date"
                min={getTodayString()}
                className="w-full p-3 bg-white text-black rounded-lg border border-gray-300 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="w-full md:w-1/3 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 transition-colors shadow-md"
            >
              {loading ? "Searching..." : "Find Routes"}
            </button>
          </div>
        </div>

        {/* RESULTS */}
        <div className="w-full max-w-3xl space-y-4 mb-20">
          {itineraries.length > 0 && (
            <div className="sticky top-[72px] z-40 bg-white/95 dark:bg-black/95 backdrop-blur py-3 text-center border-b border-gray-200 dark:border-neutral-800 mb-4 shadow-sm rounded-b-lg">
              <h3 className="text-lg font-bold text-black dark:text-white">
                Results for{" "}
                {parseDateLocal(displayDate).toLocaleDateString(undefined, {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}
              </h3>
            </div>
          )}

          {dateChanged && (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 rounded-lg border border-yellow-200 dark:border-yellow-700 text-center text-sm mb-4">
              ⚠️ No trips found on {parseDateLocal(date).toLocaleDateString()}.
              We automatically moved you to the next available date.
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800 text-center">
              {error}
            </div>
          )}

          {itineraries.map((itinerary) => (
            <div
              key={itinerary.id}
              className="bg-white dark:bg-black p-6 rounded-lg shadow-sm border-2 border-gray-200 dark:border-neutral-800 hover:shadow-md transition-all"
            >
              {itinerary.legs.map((leg: ApiLeg, i: number) => (
                <div key={i}>
                  {/* CONNECTION HEADER */}
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
                        {/* ROUTE INFO */}
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

                        <div className="text-neutral-700 dark:text-neutral-300 font-medium text-sm mt-1">
                          {formatTime(leg.departure_time)} –{" "}
                          {formatTime(leg.arrival_time)}
                        </div>

                        <div className="flex items-center gap-2 mt-2">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${leg.is_ferry ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300" : "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300"}`}
                          >
                            {leg.is_ferry ? "Ferry" : "Flight"}
                          </span>
                          <span className="text-neutral-500 dark:text-neutral-400 text-xs">
                            {leg.carrier.name} ({leg.carrier.code}) •{" "}
                            {formatDuration(leg.duration_minutes)}
                          </span>
                        </div>

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
    </div>
  );
}

export default App;
