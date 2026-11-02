import { API_URL } from '../config';
import type { ApiResponse, AvailableDatesResponse, Location } from '../types';

let locationsPromise: Promise<Location[]> | null = null;

export const fetchAvailableDates = async (
  origin: string,
  destination: string,
): Promise<AvailableDatesResponse> => {
  const params = new URLSearchParams({ origin, destination });
  const response = await fetch(
    `${API_URL}/api/routes/available-dates/?${params.toString()}`,
    { cache: 'no-store' },
  );
  if (!response.ok) {
    throw new Error('Failed to fetch available dates');
  }
  return (await response.json()) as AvailableDatesResponse;
};

export const searchRoutes = async (
  origin: string,
  destination: string,
  date?: string,
  filter = 'all',
): Promise<ApiResponse> => {
  const params = new URLSearchParams({
    origin,
    destination,
    filter,
  });
  if (date) {
    params.set('date', date);
  }
  const response = await fetch(
    `${API_URL}/api/routes/search/?${params.toString()}`,
    {
      cache: 'no-store',
    },
  );
  if (!response.ok) {
    const errorData = (await response.json()) as { error?: string };
    throw new Error(errorData.error || 'Failed to fetch routes');
  }
  return (await response.json()) as ApiResponse;
};

export const fetchLocations = async (
  signal?: AbortSignal,
): Promise<Location[]> => {
  if (!locationsPromise) {
    locationsPromise = fetch(`${API_URL}/api/locations/`, { signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch locations');
        }
        return (await response.json()) as Location[];
      })
      .catch((err: unknown) => {
        locationsPromise = null;
        throw err;
      });
  }
  return locationsPromise;
};

export const submitReport = async (
  issueType: string,
  userNote: string,
): Promise<Response> => {
  const response = await fetch(`${API_URL}/api/reports/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

