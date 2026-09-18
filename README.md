# NearCart

**Team:** Team Zyro  
**Project:** NearCart â€” Local Bazaar Discovery & Commerce Platform

## Overview

NearCart is a digital discovery layer for the local bazaar. It helps customers find nearby shops, products, services and food, compare local options, connect with businesses, confirm availability, reserve items, and choose pickup or local delivery.

**Core flow:**  
`Discover â†’ Explore â†’ Compare â†’ Connect â†’ Confirm â†’ Reserve â†’ Pickup / Delivery`

## Key Features

### Customer
- Nearby product, shop, service and food discovery
- Map-first local search with location and distance
- Universal search across products, businesses, services, food and categories
- Local price comparison
- Availability + freshness/confidence indicators
- Open/closed business status
- Separate business and product reviews
- Business recommendation system
- Chat with local businesses
- Reservation with merchant confirmation
- Pickup with QR/collection code
- Optional NearCart delivery
- Saved items, recent activity and reservation history
- Product request when an item cannot be found
- Trending Near You / Popular in Your Area
- Bazaar discovery and local specialties
- Optional AI-assisted search, voice/image search and product alternatives

### Merchant / Shopkeeper
- Business registration and claim-your-business flow
- Verified digital business profile
- Categories, subcategories and custom â€œOtherâ€ category
- Business offerings: Product / Service / Food / Other
- Product and service management
- Optional stock and availability management
- Price and offer management
- Barcode-assisted product entry
- AI-assisted product entry where available
- Customer chat
- Reservation management
- Pickup / delivery handling
- Review responses
- Profile completeness and participation level
- Discovery and activity analytics

### Business Owner
- Multi-branch management
- Branch switching
- Consolidated and branch-level analytics
- Inventory / product activity
- Reservations and operational activity
- Popular products and demand insights

### Delivery Partner
- Delivery assignments
- Pickup/drop locations
- Navigation
- Delivery status tracking
- Earnings
- Delivery history

### Admin
- Business verification
- Business claims
- User and business management
- Category management
- Review/report moderation
- Reservation and delivery oversight
- Data-quality monitoring
- Operational exceptions

## Main Functional Flow

```text
User Opens NearCart
        ↓
User Registration / Login
        ↓
Location Access / Location Selection
        ↓
Discover Nearby Businesses & Products
        ↓
Search / Filter / Compare Products
        ↓
View Product & Business Details
        ↓
Check Availability & Price
        ↓
Select Product / Add to Cart
        ↓
Place Order / Continue with Local Store
        ↓
Order Processing
        ↓
Order Status & Updates
## Business Lifecycle

```text
Business Registration
        ↓
Business Verification
        ↓
Store Profile Setup
        ↓
Product & Category Management
        ↓
Product Listing & Availability
        ↓
Customer Discovery
        ↓
Customer Interaction / Orders
        ↓
Order Fulfillment
        ↓
Business Performance Monitoring
        ↓
Profile & Product Updates
        ↺
```

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python + Flask 3.1.2 |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Authentication | Flask-Login 0.6.3 |
| Realtime | Flask-SocketIO 5.5.1 |
| Database | MySQL |
| MySQL Driver | PyMySQL 1.1.1 |
| Templates | Jinja2 |
| Frontend | HTML5 + Tailwind CSS + JavaScript |
| Maps | Leaflet / Mapbox / Google Maps Platform |
| Environment | python-dotenv 1.1.1 |
| Server Support | Werkzeug 3.1.3 + eventlet 0.40.3 |

**Python:** 3.x, using the version supported by the project environment.

## Architecture

```text
Customer / Merchant / Owner / Delivery / Admin
                    â†“
               Flask Routes
                    â†“
              Service Layer
                    â†“
             SQLAlchemy ORM
                    â†“
                 MySQL
```

Supporting services:

```text
Maps & Geolocation
Realtime Chat / Notifications
Search & Ranking
Reservation / Delivery
AI Modules (optional)
Analytics / Activity Tracking
```

## Core Status Flows

### Reservation
`PENDING â†’ CONFIRMED â†’ READY â†’ FULFILLED`  
Other states: `CANCELLED / EXPIRED`

### Delivery
`REQUESTED â†’ ASSIGNED â†’ ACCEPTED â†’ AT_SHOP â†’ PICKED_UP â†’ OUT_FOR_DELIVERY â†’ DELIVERED`  
Other state: `CANCELLED`

### Business Verification
`PENDING â†’ APPROVED / REJECTED / CORRECTION_REQUIRED / SUSPENDED`

### Business Claim
`UNCLAIMED â†’ PENDING â†’ APPROVED / REJECTED`

## Project Setup

```bash
python -m venv .venv
```

Activate the virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Configure `.env`:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST/DATABASE
SECRET_KEY=your-secret-key
MAP_API_KEY=your-map-key
AI_API_KEY=optional
```

Seed the database:

```bash
python seed.py
```

Run the application:

```bash
python run.py
```

## Demo Roles

- Customer
- Shopkeeper / Merchant
- Business Owner
- Delivery Partner
- Admin

The demo dataset should cover local business types such as electronics, grocery, mechanic/service, restaurant and street food.

## Important Design Principles

- Local businesses can be discoverable even without live inventory.
- Inventory is optional; offerings can represent products, services or food.
- Do not claim guaranteed real-time stock without a true integration.
- Show freshness so customers can judge availability.
- Merchant workflows should stay simple and low-friction.
- AI is optional and must have graceful non-AI fallbacks.
- Pickup is a valid alternative to delivery where supported.
- Trust comes from transparent verification, reviews, recommendations and freshness.
- Sensitive verification documents and private customer data must remain protected.

## Project Goal

NearCart connects the physical local market with digital discovery:

> **Find it nearby. Compare before you go.**
