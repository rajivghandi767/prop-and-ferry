# Prop & Ferry ✈️⚓

### The "Last Mile" Caribbean Routing Engine

![Status](https://img.shields.io/badge/Status-Prototype-blue) ![Stack](https://img.shields.io/badge/Stack-Django%20|%20React%20|%20Docker-green) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

**"How do I actually get there?"**

I was born and raised in Dominica 🇩🇲, and I fly home at least twice a year. Every time I do, I face the same headache, due to the fact that Dominica currently only has two nonstop flights from the mainland US: booking the flight to Antigua or Barbados is easy, but crossing that final stretch of ocean is often a nightmare.

My friends have this problem. The visitors I invite to the island have this problem.

Major aggregators (Google Flights, Expedia) are great at getting you to the Caribbean, but they fail at navigating _through_ it. They often miss the small prop planes, the inter-island ferries, and the complex connections required to reach "hard-to-get-to" gems like Dominica.

**Prop & Ferry** is my solution to this personal frustration. It’s a specialized routing engine designed to stitch together the major international legs with the regional "island hoppers" that big search engines ignore.

---

## 🏝 The "Real World" Problem

Getting to smaller Caribbean islands often requires a manual, disjointed workflow:

1.  **The Data Gap:** Regional carriers (InterCaribbean, Liat, Sunrise, Winair) and ferry services (L'Express des Iles) often don't publish full availability to the systems Google uses.
2.  **The "5-Tab" Shuffle:** Travelers have to book a jet to Antigua/Barbados/Sint Maarten etc. in one tab, then scour local airline sites in three others to find a connection, hoping the times align.
3.  **The "Visitor Barrier":** I've had friends almost cancel trips because they couldn't figure out the logistics.

## 💡 The Solution

**Prop & Ferry** acts as the intelligent middleman. It doesn't just search flights; it builds **itineraries**.

### Core Capabilities

- **Hybrid Routing:** Seamlessly combines Jet Blue/American/United flights with L'Express des Iles ferries and regional airlines in a single view.
- **"Vibe" Search (AI-Powered):** Instead of needing airport codes, users can search by intent ("Quiet jungle retreat," "Luxury beach access"), and the system maps them to the right island.
- **Award Logic:** Built-in intelligence for travel hackers. "For the American Airlines leg of this itinerary, consider using AAdvantage Miles, Alaska Atmos or British Airways Avios"

---

## 🛠 Technical Architecture

This isn't just a travel tool; it's a showcase of **Self-Hosted Microservices** running on constrained hardware (Raspberry Pi 4B).

### The Stack

- **Frontend:** React + TypeScript + Vite
- **Styling:** Tailwind CSS
- **Backend:** Python + Django REST Framework
- **Database:** PostgreSQL
- **Infrastructure:** Docker Compose (Containerized orchestration)
- **Gateway:** Nginx (Reverse proxy and static file serving)

### Infrastructure Design

Designed for the "Home Lab" environment, integrating with my existing ecosystem:

- **Zero-Cost Architecture:** Leverages scraping and "Free Tier" API strategies (Amadeus Self-Service) to minimize opex.
- **Resource Efficiency:** Uses shared database instances and optimized container builds to respect the RAM constraints of a Raspberry Pi.
- **Security:** Environment-based configuration management (`.env`), isolated Docker networks, and strict separation of Dev/Prod database users.

---

## 🗺 Roadmap

### Phase 1: The MVP (Current Status)

- [x] **Infrastructure:** Dockerized Django/React skeleton running on Nginx.
- [x] **Frontend:** Responsive landing page and search UI.
- [ ] **Core Logic:** "Airport" and "Route" database modeling.
- [ ] **Integration:** Basic API connection for major routes (Amadeus).

### Phase 2: The "Smart" Layer

- [ ] **Prop & Ferry Engine:** Custom algorithm to stitch Flight -> Ferry connections.
- [ ] **Award Mapping:** Static rules engine ("Use Avios for AA short-haul").
- [ ] **AI Integration:** LLM-based destination suggestions.

---

## 🚀 Getting Started (Local Dev)

This project follows an **Iterative MVP** methodology. You can run it locally without Docker for rapid iteration, or containerized for production parity.

### Prerequisites

- Python 3.10+
- Node.js 20+
- PostgreSQL

### 1. Clone & Setup

```bash
git clone [https://github.com/rajivghandi767/prop-and-ferry.git](https://github.com/rajivghandi767/prop-and-ferry.git)
cd prop-and-ferry
```

### 2. Backend (Django)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 3. Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

---

_This project is a personal portfolio piece demonstrating full-stack engineering capabilities, system design, and product thinking._
