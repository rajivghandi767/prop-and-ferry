# ✈️⛴️ Prop & Ferry

**Prop & Ferry** is a full-stack Caribbean travel aggregator and proof-of-concept application designed to bridge the gap between major international airline routes and regional airlines (Liat20, Winair, interCaribbean) and island-hopping ferries (like FRS Express).

As an aviation nerd born in Dominica and residing in NYC, I built this application to solve a personal pain point: many Caribbean destinations lack direct international flights, requiring complex, unlinked transfers between planes and ferries. This application automatically maps and stitches these disparate transit networks together, surfacing overnight-aware connections and providing a unified booking interface.

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
- PostgreSQL & Redis (Isolated container network)
- BeautifulSoup4 (Ferry Web Scraping)
- Duffel REST API (Flight Data)

**Infrastructure & CI/CD:**

- Self-hosted on a Raspberry Pi 4B (DietPi OS) within a Ubiquiti UniFi segmented network
- Docker & Docker Compose
- Jenkins (Automated CI/CD Deployments & ETL Pipelines)
- HashiCorp Vault (Secrets Management)
- Nginx Proxy Manager & Cloudflare (Ingress & Reverse Proxy)
- Prometheus, Grafana, & Discord Webhook Alerts

---

## 🧠 Core Architecture & Features

### 1. In-Memory Graph Traversal (The "Stitcher")

Rather than relying on computationally expensive recursive SQL queries, the backend pulls normalized route data and uses O(1) set lookups to map topologies in memory. The stitcher natively understands overnight delays, dynamically flagging connections that require a hotel stay before an onward ferry transfer.

### 2. Aggressive Redis Caching
To overcome the physical hardware limitations of the Raspberry Pi and ensure the graph traversal algorithm resolves instantly, the application utilizes **Redis** for aggressive caching. All complex multi-node route combinations are cached in-memory. This significantly reduces disk I/O on the PostgreSQL instance and implements enterprise caching best practices on constrained infrastructure.

### 3. Dual-Source ETL Pipeline

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

### Raspberry Pi Hardware Protection & Database Provisioning

To protect the host SD card from I/O degradation and database bloat:

- The PostgreSQL instance resides on a dedicated, isolated `database` Docker network preventing any external ingress. Database catalogs and user roles are dynamically provisioned via automated initialization scripts to completely segregate Prop & Ferry's data layer from other homelab applications.
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

Automated Jenkins pipelines handle the full lifecycle of the application:
- **Deployment:** Commits to `main` trigger tests, build Docker images, and deploy seamlessly via zero-downtime rolling restarts. Nightly deployments run automatically at `03:00 AM` EST. HashiCorp Vault is dynamically queried to inject runtime secrets, maintaining strict configuration management.
- **Observability Stack:** Prometheus scrapes metrics across the containers, alerting Discord via Alertmanager if memory limits or service drops are detected.

ETL pipelines manage data fetching directly within the production Docker containers via SSH:
- **Flights:** Runs at `03:30 AM` every Sunday & Wednesday.
- **Ferries:** Runs at `03:45 AM` every Sunday & Wednesday.
- **Alerting:** If Duffel returns an unknown airport code or a new airline carrier, the backend triggers a Discord Webhook, alerting the developer to enrich the database topology manually.

---

## 💻 Local Development

This section details how to replicate this environment locally. Everything is fully plug-and-play for local development without the need to manually modify `docker-compose.yml` configurations or environment paths.

### Prerequisites

**For Docker Setup (Recommended):**
- 🐳 Docker & Docker Compose

**For Manual Setup:**
- 🐍 Python 3.x
- 🟢 Node.js & npm

### Option 1: Docker (Recommended)

Local `docker-compose.yml` and `Dockerfile` configurations are already set to build directly from the source code folder for local development rather than pulling registry images. The `docker-compose.yml` is hardcoded to use `.env.example`, so absolutely no environment configuration is required.

**Spin up the stack:**
```bash
docker compose up -d --build
```
*Note: The database migrations and seed data scripts are automatically executed during container startup, securely bypassing any API restrictions!*

**Accessing Local Services:**
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`

### Option 2: Manual Setup (Non-Docker)

If you prefer running the servers manually without Docker:

**1. Start the Backend API:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r dev-requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

**2. Start the Frontend SPA:**
```bash
cd frontend
npm install
npm run dev
```

---

## 📫 Contact

Have questions or want to discuss the architecture behind this project? Feel free to reach out:

**Rajiv Wallace**  
Self-taught Software Engineer based in NYC (born in Dominica 🇩🇲). Aviation nerd, credit card points optimizer, and dedicated homelab tinkerer transitioning into tech.

- **LinkedIn**: [linkedin.com/in/rajiv-wallace](https://www.linkedin.com/in/rajiv-wallace)
- **GitHub**: [rajivghandi767](https://github.com/rajivghandi767)
- **Email**: [dev@rajivwallace.com](mailto:dev@rajivwallace.com)
