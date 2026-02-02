// 1. Basic Entities
export interface Location {
  id: number;
  code: string;
  name: string;
  city: string;
  country: string;
}

export interface Carrier {
  id: number;
  code: string;
  name: string;
  carrier_type: "AIR" | "SEA";
  website?: string;
}

// 2. The "Leg" (A single flight or ferry ride)
export interface ApiLeg {
  id: number;
  origin: Location;
  destination: Location;
  carrier: Carrier;
  
  departure_time: string; // "HH:MM:SS"
  arrival_time: string;   // "HH:MM:SS"
  duration_minutes: number;
  
  is_active: boolean;
  is_ferry: boolean;
  
  // Specific to Flights
  days_of_operation?: string; // e.g. "135" (Mon, Wed, Fri)
  
  // Specific to Ferries (or specific dates)
  price_text?: string;        // e.g. "€45.00"
  date?: string;             // YYYY-MM-DD
  
  // **NEW**: Injected by the Stitcher for UI display
  layover_text?: string;      // e.g. "2h 30m Layover in Antigua"
}

// 3. The "Itinerary" (What the UI actually renders)
export interface Itinerary {
  id: number | string;       // Can be composite "101202"
  total_duration: number;    // In minutes
  legs: ApiLeg[];            // The array of flight/ferry segments
  search_date?: string;
}

// 4. API Response Wrapper
export interface ApiResponse {
  results: Itinerary[]; 
  search_date: string;
  found_date: string;
  date_was_changed: boolean;
  error?: string;
}