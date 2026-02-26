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

interface ProjectSwitcherProps {
  align?: "left" | "right";
}

export function ProjectSwitcher({ align = "right" }: ProjectSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  const alignmentClasses =
    align === "left" ? "left-0 origin-top-left" : "right-0 origin-top-right";

  return (
    <div className="relative z-50" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-lg text-black dark:text-white hover:bg-gray-100 dark:hover:bg-neutral-900 transition-colors"
        title="More Projects"
      >
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
        <div
          className={`absolute mt-3 w-72 bg-white dark:bg-black rounded-xl shadow-xl border border-gray-200 dark:border-neutral-800 overflow-hidden transform transition-all ${alignmentClasses}`}
        >
          <div className="p-3 border-b border-gray-200 dark:border-neutral-800 bg-gray-50/50 dark:bg-neutral-900/50">
            <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
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
                className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-neutral-900 transition-colors group"
              >
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl shadow-sm ${project.color}`}
                >
                  {project.icon}
                </div>
                <div>
                  <div className="font-bold text-black dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {project.name}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 leading-tight mt-0.5">
                    {project.desc}
                  </div>
                </div>
              </a>
            ))}
          </div>

          <div className="p-2 border-t border-gray-200 dark:border-neutral-800 bg-gray-50 dark:bg-neutral-900 text-center">
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
