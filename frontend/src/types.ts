// --- UI TYPES (Used by React Components) ---
export interface Location {
  id?: number;
  code: string;
  name?: string;
  city?: string;
  country?: string;
  location_type?: 'APT' | 'PRT';
}

export interface Carrier {
  code: string;
  name: string;
  website?: string;
}

export interface Route {
  id: number;
  origin: Location;
  destination: Location;
  carrier: Carrier;
  duration_minutes: number | null;
  departure_time?: string;
  arrival_time?: string;
  days_of_operation?: string; // Now optional
  is_ferry: boolean;
  is_active: boolean;
}

export interface Itinerary {
  type: 'direct' | 'connection';
  legs: Route[];
  total_duration: number;
  connection_duration: number | null;
}

// --- API TYPES (Matches 'format_route_response' in backend/core/views.py) ---
export interface ApiRoute {
  id: number;
  carrier: string;       
  carrier_code: string; 
  type: 'AIR' | 'SEA';
  origin: string;        
  destination: string;
  
  // Names for UI
  origin_name: string;
  destination_name: string;
  origin_city: string;
  destination_city: string;

  departure_time: string;
  arrival_time: string;
  duration: number;
  is_ferry: boolean;
  
  // Optional because specific Sailings don't have generic schedules
  days_of_operation?: string; 
}

export interface ApiResponse {
  results: ApiRoute[];
  search_date: string;
  found_date: string;
  date_was_changed: boolean;
}