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

  // 1. Fetch available locations
  useEffect(() => {
    fetch(`${API_URL}/api/locations/`)
      .then((res) => res.json())
      .then((data) => setLocations(data))
      .catch((err) => console.error("Failed to load locations", err));
  }, []);

  // 2. Sync internal state when parent updates (e.g. Swap button)
  useEffect(() => {
    setQuery(value);
    // Note: We do NOT open the menu here, which is correct for Swapping.
  }, [value]);

  // 3. Filter locations when query changes
  useEffect(() => {
    if (query.length > 0) {
      const lowerQuery = query.toLowerCase();
      const results = locations.filter(
        (loc) =>
          // Use || "" to prevent crashes if city/name is missing in DB
          (loc.code || "").toLowerCase().includes(lowerQuery) ||
          (loc.city || "").toLowerCase().includes(lowerQuery) ||
          (loc.name || "").toLowerCase().includes(lowerQuery),
      );
      setFiltered(results);
    } else {
      setFiltered([]);
    }
  }, [query, locations]);

  // 4. Handle clicking outside
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
    setIsOpen(false); // Explicitly Close on Select
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onChange(val);
    // Explicitly Open on Type (if there is text)
    if (val.length > 0) {
      setIsOpen(true);
    }
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
          {filtered.map((loc) => (
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
              <div className="text-xs text-slate-400 truncate">
                {loc.name || loc.code}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
