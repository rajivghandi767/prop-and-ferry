# ✈️⛴️ Prop & Ferry

**Prop & Ferry** is a full-stack Caribbean travel aggregator and proof-of-concept application designed to bridge the gap between major international airline routes and regional airlines (Liat20, Winair, interCaribbean) and island-hopping ferries (like FRS Express).

Many Caribbean destinations (like Dominica) lack direct international flights, requiring complex, unlinked transfers between planes and ferries. This application automatically maps and stitches these disparate transit networks together, surfacing overnight-aware connections and providing a unified booking interface.

**🌍 [View the Live Demo: prop-ferry.rajivwallace.com](https://prop-ferry.rajivwallace.com)**

## ⚠️ Proof of Concept Disclaimer

This application is a Proof of Concept (POC) built to demonstrate complex system architecture, in-memory graph traversal, and API cost-optimization. It is actively maintained as an engineering portfolio piece.

While the data powering the frontend is sourced **live** via the Duffel REST API and automated web scrapers, **the booking window is intentionally restricted to a 3-day rolling forecast.** This constraint is a deliberate engineering tradeoff designed to minimize monthly API overages while keeping the core routing logic fully functional for demonstration.

---

## 📑 Table of Contents

- [🚀 Tech Stack](#-tech-stack)
- [🧠 Core Architecture & Features](#-core-architecture--features)
- [📉 Engineering Constraints & Cost Optimization](#-engineering-constraints--cost-optimization)
- [🔄 Architecture Shift: The Amadeus Deprecation](#-architecture-shift-the-amadeus-deprecation)
- [⚙️ CI/CD & Monitoring](#️-cicd--monitoring)
- [💻 Local Development](#-local-development)
- [📫 Contact](#-contact)

---

## 🚀 Tech Stack

**Frontend:**

- React 19 & TypeScript
- Tailwind CSS v4 (Custom UI with Dark/Light mode)
- Vite

**Backend:**

- Django & Django REST Framework (DRF)
- PostgreSQL (Containerized)
- BeautifulSoup4 (Ferry Web Scraping)
- Duffel REST API (Flight Data)

**Infrastructure & CI/CD:**

- Self-hosted on a Raspberry Pi 4B (DietPi OS)
- Docker & Docker Compose
- Jenkins (Automated ETL Pipelines)
- Nginx Proxy Manager & Cloudflare
- Discord Webhook Alerts

---

## 🧠 Core Architecture & Features

### 1. In-Memory Graph Traversal (The "Stitcher")

Rather than relying on computationally expensive recursive SQL queries, the backend pulls normalized route data and uses O(1) set lookups to map topologies in memory. The stitcher natively understands overnight delays, dynamically flagging connections that require a hotel stay before an onward ferry transfer.

### 2. Dual-Source ETL Pipeline

The database is actively maintained by two distinct, automated scrapers triggered by Jenkins cron jobs:

- **The Flight Scraper:** Interfaces with the Duffel REST API to pull active schedules, pricing, and seat availability.
- **The Ferry Scraper:** Uses `requests` and `BeautifulSoup` to scrape, parse, and normalize ferry schedules (FRS-Express) into the application's standard `ApiLeg` contract.

---

### 📉 System Design: Achieving a <$3.00 API Budget

Operating a live flight aggregator out-of-pocket requires strict pipeline prioritization. Because the Duffel API charges $0.005 per excess search in production, querying all theoretical Caribbean flight paths would rapidly drain resources.

To solve this, the ETL pipeline utilizes a **Domain-Driven Waterfall Discovery Strategy**:

- **The Global Constraint Map:** Transatlantic queries are hardcoded to test only valid physical realities (e.g., Paris to the French territories, London to Commonwealth hubs).
- **Ferry Hand-Offs:** The system cross-references ferry scraping data to actively suppress Duffel API calls for inter-island routes where maritime transport is the superior default.
- **Phase 1 (Network Mapping):** A "Saturday Anchor" sweep tests ~10 core trunk routes to establish the active network topology. If a regional airline drops a route, the system dynamically prunes it.
- **Phase 2 (The Targeted Sweep):** The script executes a highly targeted 3-day rolling sweep on only the confirmed active routes.

**The Math (Why 3 Days?):**
A full 14-day rolling window provides an excellent user experience but scales API calls linearly (costing over ~$75.00/year for this micro-network alone). By condensing the Jenkins cron job to run bi-weekly and strictly maintain a **3-day rolling window**, the pipeline hits roughly 70 API calls per run.

- `70 calls * 8 runs/month = 560 calls`
- `560 calls * $0.005 = $2.80 / month`

**Risk vs. Reward:** This tradeoff restricts a user's ability to plan vacations weeks in advance. However, the architectural reward is immense: it ensures a 100% live, self-healing database that seamlessly feeds the backend Stitcher (graph traversal) algorithm, proving the core routing logic operates flawlessly under enterprise constraints.

### Raspberry Pi Hardware Protection

To protect the host SD card from I/O degradation and database bloat:

- The ferry scraper executes within an `atomic` database transaction, cleanly wiping and replacing the current schedule without locking the UI.
- Both scrapers actively prune historical (past-date) transit records on initialization to keep PostgreSQL queries lightning fast.

---

### 🔄 Architecture Shift: The Amadeus Deprecation

In its original iteration, this project relied on the **Amadeus Self-Service API** and its official Python SDK. However, Amadeus has been formally deprecated from this architecture in favor of the **Duffel REST API**.

This migration was executed for three critical engineering reasons:

1. **Discontinued Developer Support:** The Amadeus Python SDK and Self-Service developer portals suffer from a lack of modern support, frequent undocumented endpoint changes, and an overall degraded developer experience.
2. **SDK Dependency Risk:** Rather than relying on an abandoned or poorly maintained third-party SDK, the new Duffel integration utilizes standard Python `requests`. This removes a fragile dependency from the project and ensures the ETL pipeline communicates directly with the modern REST endpoints.
3. **Distribution Networks:** Amadeus's free tier aggressively sandboxes real-world data and frequently fails to capture major US carriers (like American Airlines). Duffel's Direct Connect (NDC) integration and Hahn Air partnerships natively surface the exact flights required to make Caribbean island-hopping functional.

_Note: The original Amadeus scraper (`fetch_routes.py`) remains in the repository's `/commands` directory for historical context and rollback capabilities, but is flagged with a deprecation warning and is no longer executed by Jenkins._

---

## ⚙️ CI/CD & Monitoring

Automated Jenkins pipelines handle the data fetching directly within the production Docker containers via SSH:

- **Flights:** Runs at `04:30 AM` every Sunday & Wednesday.
- **Ferries:** Runs at `04:45 AM` every Sunday.
- **Alerting:** If Duffel returns an unknown airport code or a new airline carrier, the backend triggers a Discord Webhook, alerting the developer to enrich the database topology manually.

---

## 💻 Local Development

### Prerequisites

- Docker & Docker Compose
- Duffel API Token

### Quickstart

1. Clone the repository:
   ```bash
   git clone [https://github.com/rajivghandi767/prop-and-ferry.git](https://github.com/rajivghandi767/prop-and-ferry.git)
   cd prop-and-ferry
   ```
2. Set up your `.env` files (see `.env.example` in both `/backend` and `/frontend`).
3. Build and spin up the containers:
   ```bash
   docker compose up --build
   ```
4. Run migrations and populate the initial dataset:
   ```bash
   docker compose exec prop-ferry-backend python manage.py migrate
   docker compose exec prop-ferry-backend python manage.py fetch_duffel_routes
   docker compose exec prop-ferry-backend python manage.py scrape_ferries
   ```
5. Access the frontend at `http://localhost:5173` and the backend at `http://localhost:8000`.

---

## 📫 Contact

Have questions or want to discuss the architecture behind this project? Feel free to reach out:

- **Email:** [dev@rajivwallace.com](mailto:dev@rajivwallace.com)
- **GitHub:** [rajivghandi767](https://github.com/rajivghandi767)

---

_Designed & Engineered by Rajiv Wallace_
