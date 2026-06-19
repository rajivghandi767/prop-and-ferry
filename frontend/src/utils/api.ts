import { API_URL } from '../config';

export const fetchAvailableDates = async (origin: string, destination: string) => {
  const response = await fetch(
    `${API_URL}/api/routes/available-dates/?origin=${origin}&destination=${destination}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch available dates');
  }
  return response.json();
};

export const searchRoutes = async (origin: string, destination: string, date: string, filter: string = 'all') => {
  const params = new URLSearchParams({
    origin,
    destination,
    date,
    filter,
  });
  const response = await fetch(`${API_URL}/api/routes/search/?${params}`);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || "Failed to fetch routes");
  }
  return response.json();
};

export const fetchLocations = async (signal?: AbortSignal) => {
  const response = await fetch(`${API_URL}/api/locations/`, { signal });
  if (!response.ok) {
    throw new Error('Failed to fetch locations');
  }
  return response.json();
};

export const submitReport = async (issueType: string, userNote: string) => {
  const response = await fetch(`${API_URL}/api/reports/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      issue_type: issueType,
      user_note: userNote,
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to submit report');
  }
  return response;
};
