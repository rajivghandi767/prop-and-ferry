"""
Global Constants for Route Discovery.
"""

# --- FLIGHT CONFIGURATION (IATA) ---
TARGETS = ['DOM']
REGIONAL_HUBS = ['SJU', 'BGI', 'ANU', 'PTP', 'FDF',
                 'SLU', 'SXM', 'POS', 'SKB', 'SVD', 'EIS', 'STT', 'MIA', 'EWR']
GATEWAYS = ['MIA', 'JFK', 'EWR', 'ATL', 'CLT', 'IAH', 'FLL',
            'YYZ', 'YUL', 'LHR', 'LGW', 'CDG', 'ORY', 'AMS', 'FRA']

# --- FERRY CONFIGURATION (UN/LOCODE) ---

# 1. Canonical IDs (The Database Truth)
# We use UN/LOCODEs to physically distinguish Ferry Terminals from Airports.
PORT_ROSEAU = 'DMROS'      # Roseau, Dominica
PORT_PTP = 'GPPTP'      # Pointe à Pitre, Guadeloupe
PORT_FDF = 'MQFDF'        # Fort de France, Martinique
PORT_CASTRIES = 'LCCAS'    # Castries, St. Lucia

# 2. DB -> Website Input (What we type/select)
# When we want to check 'DMROS', we try these values in the dropdown.
# The scraper will try them in order until one works.
DB_TO_SITE_OPTS = {
    PORT_ROSEAU: ['DOM', 'Dominique - Roseau', 'Roseau', 'Dominique', 'Dominica'],
    PORT_PTP: ['PTP', 'Guadeloupe - Pointe à Pitre', 'Pointe a Pitre', 'Pointe-à-Pitre', 'Guadeloupe'],
    PORT_FDF:   ['FDF', 'Martinique - Fort de France', 'Fort de France', 'Fort-de-France', 'Martinique'],
    PORT_CASTRIES: ['SLU', 'Sainte Lucie - Castries', 'Castries', 'Sainte Lucie', 'Saint Lucia', 'St. Lucia'],
}

# 3. Website Output -> DB (What we save)
# If the website result says "Depart: Pointe-à-Pitre", we map it back to 'GPPTP'.
SITE_TO_DB_MAP = {
    # DOMINICA
    'DOM': PORT_ROSEAU, 'Dominique - Roseau': PORT_ROSEAU, 'Roseau': PORT_ROSEAU, 'Dominique': PORT_ROSEAU, 'Dominica': PORT_ROSEAU,
    # GUADELOUPE
    'PTP': PORT_PTP, 'Guadeloupe - Pointe à Pitre': PORT_PTP, 'Pointe à Pitre': PORT_PTP, 'Pointe-à-Pitre': PORT_PTP, 'Guadeloupe': PORT_PTP,
    # MARTINIQUE
    'FDF': PORT_FDF, 'Martinique - Fort de France': PORT_FDF, 'Fort de France': PORT_FDF, 'Fort-de-France': PORT_FDF, 'Martinique': PORT_FDF,
    # ST LUCIA
    'SLU': PORT_CASTRIES, 'Sainte Lucie - Castries': PORT_CASTRIES, 'Castries': PORT_CASTRIES, 'Sainte Lucie': PORT_CASTRIES, 'Saint Lucia': PORT_CASTRIES, 'St. Lucia': PORT_CASTRIES,
}
