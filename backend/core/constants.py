"""
Global Constants for Route Discovery, Graph Stitching, and Caching.
"""

# --- FLIGHT CONFIGURATION (IATA) ---
TARGETS: list[str] = ["DOM"]
REGIONAL_HUBS: list[str] = [
    "ANU",
    "BGI",
    "UVF",
    "PTP",
    "FDF",
    "SXM",
    "SJU",
    "EIS",
    "SKB",
]
GATEWAYS: list[str] = ["NYC", "MIA", "CLT", "LON", "PAR", "AMS", "FRA"]

# --- FERRY CONFIGURATION (UN/LOCODE) ---
# Canonical IDs (The Database Truth): UN/LOCODEs physically distinguish Ferry Terminals from Airports.
PORT_ROSEAU = "DMROS"  # Roseau, Dominica
PORT_PTP = "GPPTP"  # Pointe à Pitre, Guadeloupe
PORT_FDF = "MQFDF"  # Fort de France, Martinique
PORT_CASTRIES = "LCCAS"  # Castries, St. Lucia

FERRY_TERMINAL_CODES: frozenset[str] = frozenset(
    {PORT_ROSEAU, PORT_PTP, PORT_FDF, PORT_CASTRIES}
)

# DB -> Website Input (What the FRS Express scraper submits in the search form)
DB_TO_SITE_OPTS: dict[str, list[str]] = {
    PORT_ROSEAU: ["DOM", "Dominique - Roseau", "Roseau", "Dominique", "Dominica"],
    PORT_PTP: [
        "PTP",
        "Guadeloupe - Pointe à Pitre",
        "Pointe a Pitre",
        "Pointe-à-Pitre",
        "Guadeloupe",
    ],
    PORT_FDF: [
        "FDF",
        "Martinique - Fort de France",
        "Fort de France",
        "Fort-de-France",
        "Martinique",
    ],
    PORT_CASTRIES: [
        "SLU",
        "Sainte Lucie - Castries",
        "Castries",
        "Sainte Lucie",
        "Saint Lucia",
        "St. Lucia",
    ],
}

# --- ROUTE STITCHING & CONNECTION CONSTRAINTS ---
MIN_CONNECT_FLIGHT_SECONDS: int = 3600  # 1 Hour: Minimum time to connect plane-to-plane
MIN_CONNECT_FERRY_SECONDS: int = (
    7200  # 2 Hours: Minimum time to connect plane-to-ferry or ferry-to-plane
)
MAX_CONNECT_SECONDS: int = (
    64800  # 18 Hours: Max layover time before we consider it two separate trips
)
SEARCH_WINDOW_DAYS: int = 4  # 4-day sliding window to capture overnight connections

# --- CACHE TTLs (SECONDS) ---
CACHE_TTL_REFERENCE: int = 3600  # 1 hour for locations and carriers
CACHE_TTL_AVAILABLE_DATES: int = 900  # 15 minutes for available dates
CACHE_TTL_SEARCH: int = 300  # 5 minutes for route search results

# --- SCRAPER & DOMAIN DEFAULTS ---
DEFAULT_FERRY_DURATION_MINS: int = 120
DEFAULT_CURRENCY: str = "USD"
SOLD_OUT_LABEL: str = "Sold Out"
DUFFEL_DEFAULT_SEATS: int = 9
DUFFEL_PACING_DELAY_SECONDS: float = 0.5
DUFFEL_REQUEST_TIMEOUT_SECONDS: int = 30
DISCORD_TIMEOUT_SECONDS: int = 5
MAX_ISSUE_NOTE_LENGTH: int = 1000
