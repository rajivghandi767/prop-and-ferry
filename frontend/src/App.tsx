import { useState } from "react";
import type { Itinerary, ApiResponse } from "./types";
import { useTheme } from "./hooks/useTheme";
import { AirportSelect } from "./components/AirportSelect";
import { API_URL } from "./config";

// --- HELPERS ---

const getTodayString = () => new Date().toISOString().split("T")[0];

const formatTime = (timeStr?: string) => {
  if (!timeStr) return "";
  const [hours, minutes] = timeStr.split(":");
  const date = new Date();
  date.setHours(parseInt(hours));
  date.setMinutes(parseInt(minutes));
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
  if (days === "1234567") return "Runs Daily";
  if (days === "12345") return "Runs Mon-Fri";
  if (days === "67") return "Runs Weekends";

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

  // Search State
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState(getTodayString());

  // Results State
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
    setError(null);
    setItineraries([]); // Reset to empty array, NEVER null

    try {
      // 1. Build Query String
      const params = new URLSearchParams({
        origin: origin,
        destination: destination,
        date: date,
      });

      // 2. Fetch
      const response = await fetch(
        `http://localhost:8000/api/search/?${params}`,
      );
      const data = await response.json();

      console.log("Search response:", data); // Debug log

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch routes");
      }

      // 3. Handle Data
      // The backend now returns a direct Array, not { results: [...] }
      if (Array.isArray(data)) {
        setItineraries(data);
        if (data.length === 0) {
          setError("No routes found for this date.");
        }
      } else {
        // Fallback in case backend reverts to pagination
        setItineraries(data.results || []);
      }
    } catch (err: any) {
      console.error("Error fetching routes:", err);
      setError(err.message || "An error occurred while searching");
      setItineraries([]); // Safety reset
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col font-sans text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* --- HEADER --- */}
      <header className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm border-b border-slate-200 dark:border-slate-700 py-4 sticky top-0 z-50">
        <div className="container mx-auto px-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="text-2xl">✈️</span>
            <h1 className="text-xl font-bold text-blue-600 dark:text-blue-400">
              Prop & Ferry
            </h1>
          </div>
          <button
            onClick={toggleTheme}
            className="text-lg p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            title="Toggle Theme"
          >
            {theme === "dark" ? "🌙" : "☀️"}
          </button>
        </div>
      </header>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-grow container mx-auto px-4 py-8 flex flex-col items-center">
        {/* HERO TEXT (Optional, adds visual weight) */}
        {!itineraries.length && !loading && (
          <div className="text-center mb-10 mt-10">
            <h2 className="text-4xl font-extrabold mb-4">
              Unlock the{" "}
              <span className="text-blue-600 dark:text-blue-400">
                Hidden Caribbean
              </span>
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              Connect major flights with local island hoppers and ferries.
            </p>
          </div>
        )}

        {/* SEARCH BOX */}
        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-lg w-full max-w-4xl border border-slate-100 dark:border-slate-700 mb-8">
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
              className="p-3 rounded-full bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-blue-600 transform md:rotate-90 shadow-sm border border-slate-200 dark:border-slate-600"
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
              <label className="text-xs font-semibold text-slate-500 uppercase mb-1">
                Date
              </label>
              <input
                type="date"
                min={getTodayString()}
                className="w-full p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 dark:text-white"
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

        {/* RESULTS AREA */}
        <div className="w-full max-w-3xl space-y-4 mb-20">
          {/* STICKY DATE HEADER */}
          {itineraries.length > 0 && (
            <div className="sticky top-[72px] z-40 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur py-3 text-center border-b border-slate-200 dark:border-slate-700 mb-4 shadow-sm rounded-b-lg">
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">
                Results for{" "}
                {new Date(displayDate).toLocaleDateString(undefined, {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}
              </h3>
            </div>
          )}

          {/* DATE CHANGE ALERT */}
          {dateChanged && (
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 rounded-lg border border-yellow-200 dark:border-yellow-700 text-center text-sm mb-4">
              ⚠️ No flights found on {date}. We automatically moved you to the
              next available date.
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800 text-center">
              {error}
            </div>
          )}

          {/* CARDS */}
          {itineraries.map((itinerary, index) => (
            <div
              key={index}
              className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all"
            >
              {/* Loop through legs */}
              {itinerary.legs.map((leg, i) => (
                <div
                  key={leg.id}
                  className={`${i > 0 ? "mt-4 pt-4 border-t border-slate-100 dark:border-slate-700" : ""}`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      {/* Route Info */}
                      <div className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <span>{leg.origin.code}</span>
                        <span className="text-slate-400 text-sm">➜</span>
                        <span>{leg.destination.code}</span>
                      </div>

                      {/* Times */}
                      <div className="text-slate-700 dark:text-slate-300 font-medium text-sm mt-1">
                        {formatTime(leg.departure_time)} –{" "}
                        {formatTime(leg.arrival_time)}
                      </div>

                      {/* Carrier + Schedule */}
                      <div className="text-slate-500 dark:text-slate-400 text-xs mt-1">
                        {leg.carrier.name} ({leg.carrier.code}) •{" "}
                        {formatDuration(leg.duration_minutes)}
                        <br />
                        <span className="text-blue-500/80 dark:text-blue-400/80 italic">
                          {formatSchedule(leg.days_of_operation)}
                        </span>
                      </div>
                    </div>

                    {/* Right Side Actions */}
                    <div className="text-right flex flex-col items-end gap-2">
                      {i === 0 && (
                        <span className="inline-block bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 text-xs px-2 py-1 rounded-full font-semibold">
                          {itinerary.type === "direct" ? "Nonstop" : "1 Stop"}
                        </span>
                      )}
                      {leg.carrier.website ? (
                        <a
                          href={leg.carrier.website}
                          target="_blank"
                          rel="noreferrer"
                          className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-4 py-2 rounded-full font-bold shadow-sm"
                        >
                          Book
                        </a>
                      ) : (
                        <span className="bg-slate-100 dark:bg-slate-700 text-slate-500 text-xs px-3 py-1 rounded-full">
                          Check Airline
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* CONNECTION SUMMARY */}
              {itinerary.type === "connection" && (
                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700 flex justify-between items-center text-xs text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    ⏳ Layover in {itinerary.legs[0].destination.city}:{" "}
                    <span className="font-bold text-slate-700 dark:text-slate-300">
                      {formatDuration(itinerary.connection_duration)}
                    </span>
                  </span>
                  <span>
                    Total Trip: {formatDuration(itinerary.total_duration)}
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </main>

      {/* --- FOOTER --- */}
      <footer className="bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center items-center gap-2 mb-4">
            <span className="text-xl">✈️</span>
            <span className="font-bold text-slate-700 dark:text-slate-300">
              Prop & Ferry
            </span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mb-4">
            The easiest way to connect to the hidden gems of the Caribbean.
          </p>
          <div className="text-xs text-slate-400">
            &copy; {new Date().getFullYear()} Rajiv Wallace. All rights
            reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
