import { useState, useEffect, useRef } from "react";
import type { Location } from "../types";
import { API_URL } from "../config";

interface AirportSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

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

        // B. EXCLUSION: Hide sub-terminals (like DMROS) because their parent (DOM) handles them
        // If a location has a parent_code, it's a sub-terminal, so we hide it from the main list.
        const isHidden = loc.parent_code !== null;

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
  // Pass the entire Location object in so we can check its flags
  const getBadgeInfo = (loc: Location) => {
    // If it has children, it's a main island code like DOM or SLU
    if (loc.has_children) {
      return {
        label: "AIR / FERRY",
        className:
          "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
      };
    }
    if (loc.location_type === "PRT") {
      return {
        label: "FERRY",
        className:
          "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300",
      };
    }
    return {
      label: "AIR",
      className:
        "bg-gray-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300",
    };
  };

  return (
    <div className="flex flex-col text-left relative w-full" ref={wrapperRef}>
      <label className="text-xs font-semibold text-neutral-500 uppercase mb-1">
        {label}
      </label>

      {/* 1. Added rounded-lg to match the date input box perfectly */}
      <input
        type="text"
        placeholder={placeholder}
        className="w-full p-3 rounded-lg bg-white text-black border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder:normal-case transition-colors focus:outline-none"
        value={query}
        onChange={handleChange}
        onFocus={() => query && setIsOpen(true)}
      />

      {/* 2. Standardized dropdown menu with pure black/white and neutral borders */}
      {isOpen && filtered.length > 0 && (
        <ul className="absolute top-full left-0 right-0 mt-1 max-h-60 overflow-y-auto bg-white dark:bg-black border border-gray-200 dark:border-neutral-800 rounded-lg shadow-xl z-50">
          {filtered.map((loc) => {
            const badge = getBadgeInfo(loc);

            return (
              <li
                key={loc.id}
                onClick={() => handleSelect(loc.code)}
                className="p-3 hover:bg-gray-50 dark:hover:bg-neutral-900 cursor-pointer border-b border-gray-100 dark:border-neutral-800 last:border-0 transition-colors"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-black dark:text-white">
                    {loc.code}
                  </span>
                  <span className="text-xs text-neutral-500">
                    {loc.city || "Unknown City"}
                  </span>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-neutral-400 truncate max-w-[60%]">
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
