import { useState } from "react";
import type { Itinerary, ApiRoute } from "./types";
import { useTheme } from "./hooks/useTheme";
import { AirportSelect } from "./components/AirportSelect";
import { API_URL } from "./config";

// --- HELPERS ---

const getTodayString = () => {
  // Prevent "Yesterday" bug by getting local YYYY-MM-DD
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
      const response = await fetch(`${API_URL}/api/search/?${params}`);

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        const text = await response.text();
        console.error("Backend Error:", text);
        throw new Error("Server Error: Check backend logs.");
      }

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to fetch routes");

      // --- LOGIC: HANDLE LOOKAHEAD ---
      const rawRoutes = data.results || [];

      if (data.date_was_changed) {
        setDateChanged(true);
        setDisplayDate(data.found_date);
      } else {
        setDisplayDate(data.found_date || date);
      }

      // --- ADAPTER: MAP DATA TO UI ---
      const adaptedItineraries: Itinerary[] = rawRoutes.map((r: ApiRoute) => ({
        type: "direct",
        total_duration: r.duration,
        connection_duration: null,
        legs: [
          {
            id: r.id,
            duration_minutes: r.duration,
            departure_time: r.departure_time,
            arrival_time: r.arrival_time,

            // Only map schedule if provided (Flights). Ferries are specific dates.
            days_of_operation: r.days_of_operation || "",

            is_ferry: r.is_ferry,
            is_active: true,

            origin: {
              code: r.origin,
              name: r.origin_name,
              city: r.origin_city,
              location_type: r.is_ferry ? "PRT" : "APT",
            },
            destination: {
              code: r.destination,
              name: r.destination_name,
              city: r.destination_city,
              location_type: r.is_ferry ? "PRT" : "APT",
            },
            carrier: {
              code: r.carrier_code,
              name: r.carrier,
              // Link Logic: Ferries get explicit site, Flights check carrier
              website: r.is_ferry
                ? "https://www.express-des-iles.fr/"
                : undefined,
            },
          },
        ],
      }));

      setItineraries(adaptedItineraries);

      if (rawRoutes.length === 0) {
        setError(
          `No routes found from ${origin} to ${destination} within the next 7 days.`,
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
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col font-sans text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* HEADER */}
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
          >
            {theme === "dark" ? "🌙" : "☀️"}
          </button>
        </div>
      </header>

      {/* MAIN */}
      <main className="flex-grow container mx-auto px-4 py-8 flex flex-col items-center">
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

        {/* RESULTS */}
        <div className="w-full max-w-3xl space-y-4 mb-20">
          {/* STICKY HEADER */}
          {itineraries.length > 0 && (
            <div className="sticky top-[72px] z-40 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur py-3 text-center border-b border-slate-200 dark:border-slate-700 mb-4 shadow-sm rounded-b-lg">
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">
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

          {itineraries.map((itinerary, index) => (
            <div
              key={index}
              className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all"
            >
              {itinerary.legs.map((leg, i) => (
                <div
                  key={leg.id}
                  className={`${i > 0 ? "mt-4 pt-4 border-t border-slate-100 dark:border-slate-700" : ""}`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      {/* DISPLAY NAMES */}
                      <div className="flex flex-col">
                        <div className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <span>{leg.origin.city || leg.origin.code}</span>
                          <span className="text-slate-400 text-sm">➜</span>
                          <span>
                            {leg.destination.city || leg.destination.code}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                          {leg.origin.name} to {leg.destination.name}
                        </div>
                      </div>

                      <div className="text-slate-700 dark:text-slate-300 font-medium text-sm mt-1">
                        {formatTime(leg.departure_time)} –{" "}
                        {formatTime(leg.arrival_time)}
                      </div>

                      <div className="flex items-center gap-2 mt-2">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${leg.is_ferry ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300" : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"}`}
                        >
                          {leg.is_ferry ? "Ferry" : "Flight"}
                        </span>
                        <span className="text-slate-500 dark:text-slate-400 text-xs">
                          {leg.carrier.name} ({leg.carrier.code}) •{" "}
                          {formatDuration(leg.duration_minutes)}
                        </span>
                      </div>

                      {/* Only show "Runs Daily" if days_of_operation exists (Flights) */}
                      {leg.days_of_operation && (
                        <div className="text-blue-500/80 dark:text-blue-400/80 text-xs italic mt-1">
                          {formatSchedule(leg.days_of_operation)}
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
            </div>
          ))}
        </div>
      </main>

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
