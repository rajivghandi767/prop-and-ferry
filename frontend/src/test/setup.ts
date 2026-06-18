import { vi } from 'vitest';

vi.mock('../utils/api', () => ({
  fetchLocations: vi.fn().mockResolvedValue([
    { id: 1, code: 'JFK', name: 'John F. Kennedy International Airport', city: 'New York', location_type: 'APT', parent_code: null, has_children: false },
    { id: 2, code: 'LHR', name: 'London Heathrow Airport', city: 'London', location_type: 'APT', parent_code: null, has_children: false }
  ]),
  fetchAvailableDates: vi.fn().mockResolvedValue({ available_dates: [] }),
  searchRoutes: vi.fn().mockResolvedValue({ results: [] }),
  submitReport: vi.fn().mockResolvedValue({ ok: true })
}));
// Mock IntersectionObserver
class IntersectionObserverMock {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() { return []; }
  unobserve() {}
}
vi.stubGlobal('IntersectionObserver', IntersectionObserverMock);

