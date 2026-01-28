export interface Location {
    id: number;
    code: string;
    name: string;
    city: string;
    country: string;
    location_type: 'APT' | 'PRT'; // Airport or Port
}

export interface Carrier {
    id: number;
    code: string;
    name: string;
    carrier_type: 'AIR' | 'SEA'; // Airline or Ferry Operator
    website?: string;
}

export interface Route {
    id: number;
    origin: Location;     // Nested object (because we used nested serializers)
    destination: Location;
    carrier: Carrier;
    duration_minutes: number | null; // Can be null in DB
    departure_time?: string; // Format "14:30:00"
    arrival_time?: string;
    days_of_operation: string[]; // E.g., ['Mon', 'Wed', 'Fri']
    is_active: boolean;
}

export interface Itinerary {
  type: 'direct' | 'connection';
  legs: Route[];
  total_duration: number;
  connection_duration: number | null;
}

export interface ApiResponse {
  results: Itinerary[];
  search_date: string;
  found_date: string | null;
  date_was_changed: boolean;
}