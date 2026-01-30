import { useState, useEffect, useRef } from "react";
import type { Location } from "../types";
import { API_URL } from "../config";

interface AirportSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

// 1. CONFIG: Ports to hide because they are covered by the main island code
const HIDDEN_CODES = ["DMROS", "GPPTP", "MQFDF", "LCCAS"];

// 2. CONFIG: Hubs that should show "AIR / FERRY" because they search both
const HYBRID_CODES = ["DOM", "PTP", "FDF", "SLU"];

export function AirportSelect({
  label,
  value,
  onChange,
  placeholder,
}: AirportSelectProps) {
  const [query, setQuery] = useState(value);
  const [locations, setLocations] = useState<Location[]>([]);
  const [filtered, setFiltered] = useState<Location[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch locations
  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_URL}/api/locations/`, { signal: controller.signal })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setLocations(data);
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Failed to load locations", err);
        }
      });

    return () => controller.abort();
  }, []);

  // Sync state
  useEffect(() => {
    setQuery(value);
  }, [value]);

  // Filter Logic
  useEffect(() => {
    if (query.length > 0) {
      const lowerQuery = query.toLowerCase();
      const results = locations.filter((loc) => {
        // A. Basic Search Match
        const matchesSearch =
          (loc.code || "").toLowerCase().includes(lowerQuery) ||
          (loc.city || "").toLowerCase().includes(lowerQuery) ||
          (loc.name || "").toLowerCase().includes(lowerQuery);

        // B. EXCLUSION: Hide the specific ferry ports (User wants DOM, not DMROS)
        const isHidden = HIDDEN_CODES.includes(loc.code);

        return matchesSearch && !isHidden;
      });
      setFiltered(results);
    } else {
      setFiltered([]);
    }
  }, [query, locations]);

  // Click Outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (code: string) => {
    setQuery(code);
    onChange(code);
    setIsOpen(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onChange(val);
    if (val.length > 0) setIsOpen(true);
  };

  // Helper to determine Badge Style & Text
  const getBadgeInfo = (code: string, type: string) => {
    if (HYBRID_CODES.includes(code)) {
      return {
        label: "AIR / FERRY",
        className:
          "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
      };
    }
    if (type === "PRT") {
      return {
        label: "FERRY",
        className:
          "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
      };
    }
    return {
      label: "AIR",
      className:
        "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    };
  };

  return (
    <div className="flex flex-col text-left relative w-full" ref={wrapperRef}>
      <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">
        {label}
      </label>
      <input
        type="text"
        placeholder={placeholder}
        className="w-full p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white uppercase placeholder:normal-case transition-colors"
        value={query}
        onChange={handleChange}
        onFocus={() => query && setIsOpen(true)}
      />

      {/* Dropdown Menu */}
      {isOpen && filtered.length > 0 && (
        <ul className="absolute top-full left-0 right-0 mt-1 max-h-60 overflow-y-auto bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl z-50">
          {filtered.map((loc) => {
            const badge = getBadgeInfo(loc.code, loc.location_type || "APT");

            return (
              <li
                key={loc.id}
                onClick={() => handleSelect(loc.code)}
                className="p-3 hover:bg-blue-50 dark:hover:bg-slate-700 cursor-pointer border-b border-slate-100 dark:border-slate-700 last:border-0"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-slate-900 dark:text-white">
                    {loc.code}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {loc.city || "Unknown City"}
                  </span>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-slate-400 truncate max-w-[60%]">
                    {loc.name || loc.code}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-bold whitespace-nowrap ${badge.className}`}
                  >
                    {badge.label}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
