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
}

export interface Route {
    id: number;
    origin: Location;     // Nested object (because we used nested serializers)
    destination: Location;
    carrier: Carrier;
    duration_minutes: number | null; // Can be null in DB
    is_active: boolean;
}