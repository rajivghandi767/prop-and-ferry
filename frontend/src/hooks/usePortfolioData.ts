import { useState, useEffect } from "react";

export interface PortfolioProject {
  title: string;
  deployed_url: string;
  description: string;
  technology: string;
  emoji?: string;
}

export interface PortfolioInfo {
  github_url: string;
  email: string;
}

interface PaginatedResponse<T> {
  results?: T[];
}

function extractList<T>(data: PaginatedResponse<T> | T[]): T[] {
  if (Array.isArray(data)) {
    return data;
  }
  return Array.isArray(data.results) ? data.results : [];
}

let projectsPromise: Promise<PortfolioProject[]> | null = null;
let infoPromise: Promise<PortfolioInfo | null> | null = null;

function fetchPortfolioProjects(): Promise<PortfolioProject[]> {
  if (!projectsPromise) {
    projectsPromise = fetch("https://portfolio-api.rajivwallace.com/api/projects/")
      .then(async (res) => {
        const data = (await res.json()) as PaginatedResponse<PortfolioProject> | PortfolioProject[];
        return extractList(data);
      })
      .catch((err: unknown) => {
        projectsPromise = null;
        throw err;
      });
  }
  return projectsPromise;
}

function fetchPortfolioInfo(): Promise<PortfolioInfo | null> {
  if (!infoPromise) {
    infoPromise = fetch("https://portfolio-api.rajivwallace.com/api/info/")
      .then(async (res) => {
        const data = (await res.json()) as PaginatedResponse<PortfolioInfo> | PortfolioInfo[];
        const results = extractList(data);
        return results.length > 0 ? results[0] : null;
      })
      .catch((err: unknown) => {
        infoPromise = null;
        throw err;
      });
  }
  return infoPromise;
}

export function usePortfolioData(): {
  projects: PortfolioProject[];
  info: PortfolioInfo | null;
} {
  const [projects, setProjects] = useState<PortfolioProject[]>([]);
  const [info, setInfo] = useState<PortfolioInfo | null>(null);

  useEffect(() => {
    void fetchPortfolioProjects()
      .then(setProjects)
      .catch(console.error);

    void fetchPortfolioInfo()
      .then(setInfo)
      .catch(console.error);
  }, []);

  return { projects, info };
}

