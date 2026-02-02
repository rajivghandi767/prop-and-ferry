import { useState, useRef, useEffect } from "react";

const PROJECTS = [
  {
    name: "Portfolio",
    url: "https://rajivwallace.com",
    icon: "👨🏾‍💻",
    desc: "My professional journey & resume",
    color:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  },
  {
    name: "Country Trivia",
    url: "https://trivia.rajivwallace.com",
    icon: "🌍",
    desc: "Test your geography knowledge",
    color:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  },
  {
    name: "Prop & Ferry",
    url: "https://prop-ferry.rajivwallace.com",
    icon: "✈️",
    desc: "Caribbean island hopping made easy",
    color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
];

export function ProjectSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400"
        title="More Projects"
      >
        {/* Waffle Icon (Grid) */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="3" width="7" height="7"></rect>
          <rect x="14" y="3" width="7" height="7"></rect>
          <rect x="14" y="14" width="7" height="7"></rect>
          <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-3 w-72 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-100 dark:border-slate-700 overflow-hidden z-50 transform origin-top-right transition-all">
          <div className="p-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Projects by Rajiv
            </h3>
          </div>

          <div className="p-2 grid gap-1">
            {PROJECTS.map((project) => (
              <a
                key={project.name}
                href={project.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group"
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl shadow-sm ${project.color}`}
                >
                  {project.icon}
                </div>
                <div>
                  <div className="font-bold text-slate-700 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {project.name}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 leading-tight mt-0.5">
                    {project.desc}
                  </div>
                </div>
              </a>
            ))}
          </div>

          <div className="p-2 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/30 text-center">
            <a
              href="https://github.com/rajivghandi767"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
            >
              View Rajiv's GitHub Repo →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
