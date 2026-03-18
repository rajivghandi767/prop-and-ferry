# ✈️⛴️ Prop & Ferry

**Prop & Ferry** is a full-stack Caribbean travel aggregator and proof-of-concept application designed to bridge the gap between major international airline routes and regional airlines (Liat20, Winair, interCaribbean) and island-hopping ferries (like FRS Express).

Many Caribbean destinations (like Dominica) lack direct international flights, requiring complex, unlinked transfers between planes and ferries. This application automatically maps and stitches these disparate transit networks together, surfacing overnight-aware connections and providing a unified booking interface.

**🌍 [View the Live Demo: prop-ferry.rajivwallace.com](https://prop-ferry.rajivwallace.com)**

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
- Amadeus API (Flight Data)

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

- **The Flight Scraper:** Interfaces with the Amadeus API to pull active schedules, pricing, and seat availability.
- **The Ferry Scraper:** Uses `requests` and `BeautifulSoup` to scrape, parse, and normalize ferry schedules (FRS-Express) into the application's standard `ApiLeg` contract.

---

## 📉 Engineering Constraints & Cost Optimization

As a proof of concept running on a self-hosted Homelab, this project prioritizes extreme cost-efficiency, lean resource management, and hardware longevity.

### Achieving a $0.00 API Budget

Amadeus API queries are strictly constrained to remain within the Self-Service Free Tier (~3,000 calls/month). To achieve continuous coverage without incurring charges:

- **MAC Compression:** International origins are restricted to Metropolitan Area Codes (`NYC`, `LON`, `PAR`). This forces the API to search up to a dozen physical airports simultaneously while only charging for 3 API requests.
- **Rolling 14-Day Window:** The CI/CD pipeline runs a bi-weekly sweep, overwriting the database to maintain a highly accurate, rolling two-week booking window that naturally catches airline cancellations and sold-out inventory.

### Raspberry Pi Hardware Protection

To protect the host SD card from I/O degradation and database bloat:

- The ferry scraper executes within an `atomic` database transaction, cleanly wiping and replacing the current schedule without locking the UI.
- Both scrapers actively prune historical (past-date) transit records on initialization to keep PostgreSQL queries lightning fast.

---

## ⚙️ CI/CD & Monitoring

Automated Jenkins pipelines handle the data fetching directly within the production Docker containers via SSH:

- **Flights:** Runs at `04:30 AM` on the 1st and 15th of the month.
- **Ferries:** Runs at `04:45 AM` every Sunday.
- **Alerting:** If Amadeus returns an unknown airport code or a new airline carrier, the backend triggers a Discord Webhook, alerting the developer to enrich the database topology manually.

---

## 💻 Local Development

### Prerequisites

- Docker & Docker Compose
- Amadeus API Keys

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
   docker compose exec prop-ferry-backend python manage.py fetch_routes
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
