export interface Location {
  id: number;
  code: string;
  name: string;
  city?: string;
  country?: string;
  location_type: string;
  parent_code?: string | null;
  has_children?: boolean;
}

export interface LegEndpoint {
  code: string;
  name: string;
  city?: string;
}

export interface ApiLeg {
  is_ferry: boolean;
  origin: LegEndpoint;
  destination: LegEndpoint;
  carrier: {
    code: string;
    name: string;
    website?: string;
  };
  departure_date: string;
  arrival_date: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  flight_number?: string;
  aircraft_type?: string;
  days_of_operation?: string;

  // Cleaned up Pricing & Seats
  price_text?: string;
  available_seats?: number;
  is_sold_out?: boolean;

  layover_text?: string;
  last_seen_at?: string;
}

export interface Itinerary {
  id: string;
  is_sold_out?: boolean;
  legs: ApiLeg[];
}

export interface AvailableDatesResponse {
  available_dates: string[];
  window_start?: string;
  window_end?: string;
}

export interface ApiResponse {
  date_was_changed: boolean;
  found_date: string;
  results: Itinerary[];
  available_dates?: string[];
  window_start?: string;
  window_end?: string;
}
