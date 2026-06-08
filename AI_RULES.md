# AI Assistant Rules

The following rules must be strictly adhered to by any AI agent or assistant modifying this codebase:

## 1. Branch Management & Archives
- **CRITICAL**: NEVER delete, modify, or prune any local or remote branches prefixed with `archive/` (e.g., `archive/linkedin-reach-submission`). These branches are permanent, immutable snapshots and must be preserved.

## 2. DRY Architecture (Don't Repeat Yourself)
- Do not hardcode global portfolio elements in the frontend UI.
- All common data (projects, short descriptions, emojis, tech stacks, email addresses, GitHub links, LinkedIn links) must be dynamically fetched from the centralized `portfolio-website` API (e.g., `https://portfolio-api.rajivwallace.com/api/projects/` and `https://portfolio-api.rajivwallace.com/api/info/`).
- Use the `usePortfolioData` React hook to retrieve this data rather than duplicating it.

## 3. UI Layout Conventions
- **Project Switcher**: The Project Switcher component must exclusively list the user's software projects alongside their short descriptions and dynamic emoji/technology icons.
- **Footer**: Global social and contact links (Email, LinkedIn, GitHub) belong exclusively in the Footer component, not the Project Switcher.

## 4. Nginx & CORS
- Any Nginx configuration block that dynamically sets the `Access-Control-Allow-Origin` header MUST also include `add_header Vary Origin always;` (or `add_header Vary Origin;` in `OPTIONS` blocks). This prevents browsers and CDNs (like Cloudflare) from caching a CORS response for one subdomain and improperly reusing it for a different subdomain.
