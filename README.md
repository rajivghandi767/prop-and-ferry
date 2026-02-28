# Prop & Ferry ✈️⚓

### The "Last Mile" Caribbean Routing Engine

![Status](https://img.shields.io/badge/Status-Prototype-blue) ![Stack](https://img.shields.io/badge/Stack-Django%20|%20React%20|%20Docker-green) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

**"How do I actually get there?"**

I was born and raised in Dominica 🇩🇲. Because the island has limited direct flights from the mainland US, traveling home is a logistical puzzle. Getting to nearby hubs like Antigua or Barbados is easy, but crossing that final stretch of ocean is often a nightmare.

Major aggregators (Google Flights, Expedia) are excellent at getting you to the Caribbean, but they fail at navigating _through_ it. They often lack data for small prop planes, inter-island ferries, and the complex, multi-modal connections required to reach "hard-to-get-to" gems.

**Prop & Ferry** is my engineering solution to this real-world business problem. It’s a specialized routing engine designed to stitch together major international flight legs with the regional "island hoppers" and maritime routes that big search engines ignore.

---

## 💡 The Product Solution

**Prop & Ferry** acts as an intelligent middleman. It doesn't just search flights; it builds **comprehensive itineraries**.

This project demonstrates strong **product-minded engineering**—identifying a fragmented data ecosystem and building a centralized, user-friendly solution to solve it.

### Core Capabilities

- **Hybrid Routing:** Seamlessly combines major airline data (JetBlue, American) with localized transport (L'Express des Iles ferries, regional prop carriers) into a single, navigable view.
- **Award Travel Logic:** Built-in intelligence for travel optimization. The system suggests loyalty program strategies (e.g., "Consider using British Airways Avios for this short-haul American Airlines leg").
- **"Vibe" Search (Roadmap):** Allowing users to search by intent ("Quiet jungle retreat") rather than just airport codes, utilizing LLMs to map intent to specific islands.

---

## 🛠 Technical Architecture & System Design

This tool is a showcase of building **Self-Hosted Microservices** and designing data pipelines to handle unstructured and un-federated data sources.

### The Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** Python + Django REST Framework
- **Database:** PostgreSQL
- **Infrastructure:** Docker Compose, Nginx, Linux (Raspberry Pi 4B)

### Engineering Highlights

- **Data Aggregation Strategy:** To keep operational costs at zero (Zero-Cost Architecture), the backend leverages a mix of the Amadeus Self-Service API (free tier) and targeted web scraping scripts to pull in ferry and regional flight schedules that aren't available on standard GDS (Global Distribution Systems).
- **Custom Routing Algorithm:** Designed backend logic to calculate feasible layovers between distinct modes of transport (e.g., ensuring a user has enough time to take a taxi from the airport to the ferry terminal).
- **Resource Efficiency:** Built to run smoothly within the constrained RAM and CPU limits of a Raspberry Pi home lab, relying on optimized container builds, shared database instances, and efficient database query structuring.

---

## 🗺 Roadmap & Iteration

This project follows an **Iterative MVP** methodology.

### Phase 1: The MVP (Current Status)

- [x] **Infrastructure:** Dockerized Django/React skeleton running via Nginx reverse proxy.
- [x] **Frontend:** Responsive landing page and dynamic search UI.
- [x] **Data Modeling:** Complex relational models for Carriers, Locations, Routes, and Transport Modes.
- [x] **Ferry Data Pipeline:** Custom Django management commands to scrape and seed regional ferry schedules.

### Phase 2: The "Smart" Layer (In Progress)

- [ ] **Prop & Ferry Algorithm:** Finalizing the custom algorithm to stitch Flight -> Ferry connections seamlessly.
- [ ] **Live API Integration:** Connecting the Amadeus API to pull real-time jet availability to regional hubs.
- [ ] **AI Integration:** Implementing LLM-based destination intent mapping.

---

## 🚀 Getting Started (Local Dev)

You can run this project locally without Docker for rapid iteration, or utilize the provided Dockerfiles for production parity.

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

# Setup Database and run migrations
python manage.py migrate

# Seed the database with scraped ferry routes
python manage.py scrape_ferries
python manage.py runserver
```

### 3. Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

---

_This project is a personal portfolio piece demonstrating full-stack engineering capabilities, data aggregation, system design, and product thinking._
