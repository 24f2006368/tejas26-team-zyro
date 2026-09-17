# tejas26-team-zyro
TEJAS TEAM ZYRO, NearCart is a digital map of the local bazaar that helps users discover nearby shops, products, services, and street food, compare prices, connect with merchants, check availability, reserve products, and choose self-pickup or local delivery.
# NearCart — Your Local Bazaar, Mapped.

NearCart is a digital discovery and commerce prototype for local bazaars. It maps nearby shops,
services, street-food stalls and specialties; lets customers compare prices, read reviews, chat
with shopkeepers, confirm availability, reserve products, and choose pickup or delivery.

Core loop: **Discover → Explore → Compare → Connect → Confirm → Reserve → Pickup/Delivery**

## Prototype engineering choices

The build prompt specifies MySQL and Google Maps/Mapbox. For a prototype that runs with zero
external setup, two substitutions were made — both isolated so they're swappable later:

- **Database:** SQLite instead of MySQL. Models are plain SQLAlchemy with no SQLite-only
  features, so pointing `DATABASE_URL` at a `mysql+pymysql://...` URL is the only change needed.
- **Map:** Leaflet + OpenStreetMap tiles instead of Google Maps/Mapbox (no paid API key needed).
  All provider-specific logic lives in `app/services/map_service.py`.

Everything else follows the spec: Flask + Blueprints (MVC), SQLAlchemy, Flask-Login,
Flask-SocketIO for chat, Tailwind (CDN) + Jinja2, no React, no OTP auth.

## Features implemented

- Auth (customer signup, shopkeeper multi-step registration, admin), role-based access control
- Business listing, categories, business offerings (lightweight catalogue) and detailed products/services
- Interactive map with marker clustering, nearby search, category filters, route/ETA preview
- Product search, price comparison across shops, product alternatives
- Shop, product and service reviews (separate) + customer recommendation percentage
  (hidden until there's enough sample size, weighted toward verified interactions)
- Real-time customer ↔ shopkeeper chat (Flask-SocketIO) with quick actions, product-context chat
- Reservation state machine (PENDING → CONFIRMED → READY → FULFILLED, with REJECTED/CANCELLED/EXPIRED)
- Self pickup with a collection code, and optional local delivery with a delivery-partner workflow
- Admin verification queue (approve/reject/request correction), document review, business
  suspension, review moderation, reports/moderation queue, category management
- Barcode "scan" flow (manual-entry fallback; a real camera scanner library can be dropped into
  the existing modal in `shopkeeper/products.html`)
- Optional AI query interpretation (`app/services/ai_service.py`) — degrades gracefully with no key
- Trending vs. Popular (kept as separate concepts) based on logged activity events
- JSON API endpoints under `/api/...` so a future React/mobile frontend can reuse the backend
- Empty states, error pages (no stack traces), CSRF protection, private (non-public) storage for
  verification documents, backend-enforced role checks everywhere

## Not fully built (explicitly out of scope for a first prototype per the build prompt)

- AI-assisted product-entry-from-photo and voice search are stubbed (no external AI wired in)
- Delivery partner dashboard is minimal/operational only, as specified
- No dedicated analytics dashboards beyond the admin overview counts
