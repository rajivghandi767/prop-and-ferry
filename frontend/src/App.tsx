import { useState } from "react";

function App() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 py-4">
        <div className="container mx-auto px-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            {/* Simple Plane Icon */}
            <span className="text-2xl">✈️</span>
            <h1 className="text-xl font-bold tracking-tight text-blue-600">
              Prop & Ferry
            </h1>
          </div>
          <nav>
            <button className="text-sm font-medium text-slate-600 hover:text-blue-600 cursor-pointer">
              Login
            </button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-grow container mx-auto px-4 py-16 flex flex-col items-center text-center">
        <h2 className="text-4xl md:text-5xl font-extrabold mb-6 text-slate-900">
          Unlock the Caribbean's <br />
          <span className="text-blue-600">Hidden Routes</span>
        </h2>
        <p className="text-lg text-slate-600 max-w-2xl mb-10">
          The only tool that combines major airlines, regional island hoppers,
          and local ferries to get you to Dominica🇩🇲 and the rest of the Eastern
          Caribbean.
        </p>

        {/* Search Mockup */}
        <div className="bg-white p-6 rounded-xl shadow-lg w-full max-w-3xl border border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col text-left">
              <label className="text-xs font-semibold text-slate-500 uppercase mb-1">
                From
              </label>
              <input
                type="text"
                placeholder="JFK, MIA, LHR..."
                className="w-full p-3 bg-slate-50 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
              />
            </div>
            <div className="flex flex-col text-left">
              <label className="text-xs font-semibold text-slate-500 uppercase mb-1">
                To
              </label>
              <input
                type="text"
                placeholder="DOM, SLU, PTP..."
                className="w-full p-3 bg-slate-50 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
              />
            </div>
            <div className="flex items-end">
              <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200 cursor-pointer">
                Find Routes
              </button>
            </div>
          </div>
        </div>

        <div className="mt-12 text-sm text-slate-400">
          Currently tracking routes for:{" "}
          <span className="font-semibold text-slate-600">
            Dominica (DOM), St. Lucia (SLU), Guadeloupe (PTP)
          </span>
        </div>
      </main>
    </div>
  );
}

export default App;
