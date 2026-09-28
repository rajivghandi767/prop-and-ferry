interface ShowcaseCorridor {
  id: string;
  origin: string;
  destination: string;
  title: string;
  badge: string;
}

const SHOWCASE_CORRIDORS: ShowcaseCorridor[] = [
  {
    id: "nyc-dom",
    origin: "NYC",
    destination: "DOM",
    title: "🗽 New York → Dominica",
    badge: "Nonstop or Stitched",
  },
  {
    id: "mia-dom",
    origin: "MIA",
    destination: "DOM",
    title: "🏖️ Miami → Dominica",
    badge: "Direct / Feeder",
  },
  {
    id: "par-dom",
    origin: "PAR",
    destination: "DOM",
    title: "🥐 Paris → Dominica",
    badge: "Flight + Ferry",
  },
  {
    id: "lon-dom",
    origin: "LON",
    destination: "DOM",
    title: "🇬🇧 London → Dominica",
    badge: "Stitched Flight",
  },
];

interface ShowcasePillsProps {
  onSelectRoute: (origin: string, destination: string) => void;
  currentOrigin?: string;
  currentDestination?: string;
  disabled?: boolean;
}

export function ShowcasePills({
  onSelectRoute,
  currentOrigin,
  currentDestination,
  disabled = false,
}: ShowcasePillsProps) {
  return (
    <div className="w-full max-w-4xl px-2 mb-4 animate-fade-in">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
          ✨ Verified Showcase Corridors (Test Transit Stitching)
        </span>
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 hidden sm:inline">
          1-Click to Test
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {SHOWCASE_CORRIDORS.map((c) => {
          const isActive =
            currentOrigin?.toUpperCase() === c.origin &&
            currentDestination?.toUpperCase() === c.destination;

          return (
            <button
              key={c.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelectRoute(c.origin, c.destination)}
              className={`p-3 rounded-lg border text-center transition-all duration-150 cursor-pointer flex flex-col items-center justify-center gap-1.5 ${
                isActive
                  ? "bg-brand-light/10 dark:bg-brand-dark/15 border-brand-light dark:border-brand-dark ring-1 ring-brand-light dark:ring-brand-dark"
                  : "bg-gray-50/70 dark:bg-neutral-900/60 border-gray-200 dark:border-neutral-800 hover:border-brand-light/60 dark:hover:border-brand-dark/60 hover:bg-gray-100/80 dark:hover:bg-neutral-900"
              } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <span className="font-bold text-xs text-black dark:text-white leading-snug text-center w-full">
                {c.title}
              </span>
              <span className="text-[9px] font-semibold px-2 py-0.5 rounded bg-brand-light/10 dark:bg-brand-dark/20 text-brand-light dark:text-brand-dark">
                {c.badge}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
