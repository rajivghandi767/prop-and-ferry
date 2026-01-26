import { useState } from "react";
import type { Route } from "./types";
import { useTheme } from "./hooks/useTheme";

function App() {
  // Custom Hook for Dark Mode
  const { theme, toggleTheme } = useTheme();

  // Local State
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    // Basic validation
    if (!origin || !destination) {
      setError("Please enter both Origin and Destination");
      return;
    }

    setLoading(true);
    setError("");
    setRoutes([]);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/routes/?origin=${origin}&destination=${destination}`,
      );

      if (!response.ok) {
        throw new Error("Server error");
      }

      const data = await response.json();
      setRoutes(data);

      if (data.length === 0) {
        setError("No routes found. Try MIA to DOM.");
      }
    } catch (err) {
      setError("Failed to fetch routes. Is the backend running?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col font-sans text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 py-4 transition-colors duration-200">
        <div className="container mx-auto px-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="text-2xl">✈️</span>
            <h1 className="text-xl font-bold tracking-tight text-blue-600 dark:text-blue-400">
              Prop & Ferry
            </h1>
          </div>
          <nav className="flex items-center gap-4">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors text-lg"
              title="Toggle Theme"
              aria-label="Toggle Dark Mode"
            >
              {theme === "dark" ? "🌙" : "☀️"}
            </button>
            <button className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer">
              Login
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-grow container mx-auto px-4 py-16 flex flex-col items-center text-center">
        <h2 className="text-4xl md:text-5xl font-extrabold mb-6 text-slate-900 dark:text-white transition-colors">
          Unlock the Caribbean's <br />
          <span className="text-blue-600 dark:text-blue-400">
            Hidden Routes
          </span>
        </h2>
        <p className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mb-10 transition-colors">
          The only tool that combines major airlines, regional island hoppers,
          and local ferries to get you to Dominica🇩🇲 and the rest of the Eastern
          Caribbean.
        </p>

        {/* Search Box */}
        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-lg w-full max-w-3xl border border-slate-100 dark:border-slate-700 transition-colors duration-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Origin Input */}
            <div className="flex flex-col text-left">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">
                From
              </label>
              <input
                type="text"
                placeholder="JFK, MIA..."
                className="w-full p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white uppercase placeholder:normal-case transition-colors"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
              />
            </div>

            {/* Destination Input */}
            <div className="flex flex-col text-left">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">
                To
              </label>
              <input
                type="text"
                placeholder="DOM, SLU..."
                className="w-full p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white uppercase placeholder:normal-case transition-colors"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
              />
            </div>

            {/* Search Button */}
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {loading ? "Searching..." : "Find Routes"}
              </button>
            </div>
          </div>
        </div>

        {/* Results Area */}
        <div className="w-full max-w-3xl text-left space-y-4 mt-10">
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800 text-center animate-pulse">
              {error}
            </div>
          )}

          {routes.map((route) => (
            <div
              key={route.id}
              className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border border-slate-100 dark:border-slate-700 flex justify-between items-center hover:shadow-md transition-all"
            >
              <div>
                <div className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <span>{route.origin.code}</span>
                  <span className="text-slate-400 text-sm">➜</span>
                  <span>{route.destination.code}</span>
                </div>
                <div className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                  {route.carrier.name} •{" "}
                  {route.duration_minutes
                    ? `${route.duration_minutes} mins`
                    : "Duration N/A"}
                </div>
              </div>
              <div className="text-right">
                <span className="inline-block bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 text-xs px-2 py-1 rounded-full font-semibold border border-green-200 dark:border-green-800">
                  Available
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-sm text-slate-400">
          Currently tracking routes for:{" "}
          <span className="font-semibold text-slate-600 dark:text-slate-300">
            Dominica (DOM), St. Lucia (SLU), Guadeloupe (PTP)
          </span>
        </div>
      </main>
    </div>
  );
}

export default App;
