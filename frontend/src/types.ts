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

export interface ApiLeg {
  is_ferry: boolean;
  origin: Location;
  destination: Location;
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
  price_text?: string;
  layover_text?: string;
  last_seen_at?: string;
}

export interface Itinerary {
  id: string;
  legs: ApiLeg[];
}

export interface ApiResponse {
  date_was_changed: boolean;
  found_date: string;
  results: Itinerary[];
}