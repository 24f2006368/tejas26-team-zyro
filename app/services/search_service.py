"""Core nearby/search query (doc #70, #57). MVP keyword + category + distance
ranking; a dedicated search engine can replace this module later without
touching controllers."""
from sqlalchemy import or_, and_

from app.extensions import db
from app.constants import VerificationStatus, ProductStatus
from app.models.shop import Shop
from app.models.product import Product
from app.models.service import Service
from app.models.category import Category
from app.services.location_service import haversine_km, bounding_box


def _verified_shops_query():
    """Public discovery must only surface businesses the admin has approved
    ("Allow only approved businesses/products in public discovery"). Pending,
    rejected, correction-required and suspended shops are all excluded."""
    return Shop.query.filter(Shop.verification_status == VerificationStatus.APPROVED)


def _tokens_filter(columns, query):
    """Matches when every word in the query appears (in any order, across any
    of `columns`) — so "Samsung 25W charger" matches a listing named
    "Samsung 25W Fast Charger" instead of requiring an exact substring."""
    tokens = [t for t in query.strip().split() if t]
    if not tokens:
        return None
    return and_(*[
        or_(*[col.ilike(f"%{token}%") for col in columns])
        for token in tokens
    ])


def nearby_shops(lat, lon, radius_km=5.0, category_type=None, query=None, limit=100):
    """Returns shops within radius, each annotated with .distance_km, sorted nearest first."""
    q = _verified_shops_query()

    if lat is not None and lon is not None:
        lat_min, lat_max, lon_min, lon_max = bounding_box(lat, lon, radius_km)
        q = q.filter(Shop.latitude.between(lat_min, lat_max),
                     Shop.longitude.between(lon_min, lon_max))

    if category_type:
        q = q.join(Category, Shop.category_id == Category.id).filter(Category.type == category_type)

    if query:
        condition = _tokens_filter([Shop.name, Shop.description], query)
        if condition is not None:
            q = q.filter(condition)

    shops = q.limit(500).all()

    results = []
    for shop in shops:
        distance = haversine_km(lat, lon, shop.latitude, shop.longitude) if lat is not None else None
        if lat is not None and (distance is None or distance > radius_km):
            continue
        shop.distance_km = distance
        results.append(shop)

    results.sort(key=lambda s: (s.distance_km if s.distance_km is not None else 1e9))
    return results[:limit]


def search_products(query, lat=None, lon=None, radius_km=5.0, sort="relevance", limit=100):
    """Product search across shops, with price/distance/rating available for
    price-comparison sorting (doc #19/#25). Also matches the product's
    category name so a category-level intent still finds products in it."""
    q = (
        Product.query.join(Shop, Product.shop_id == Shop.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .filter(Product.status == ProductStatus.ACTIVE)
        .filter(Shop.verification_status == VerificationStatus.APPROVED)
    )
    if query:
        condition = _tokens_filter([Product.name, Product.brand, Category.name], query)
        if condition is not None:
            q = q.filter(condition)

    products = q.limit(500).all()

    results = []
    for p in products:
        shop = p.shop
        distance = haversine_km(lat, lon, shop.latitude, shop.longitude) if lat is not None else None
        if lat is not None and radius_km and distance is not None and distance > radius_km:
            continue
        p.distance_km = distance
        results.append(p)

    if sort == "price_low":
        results.sort(key=lambda p: (p.discounted_price if p.discounted_price is not None else 1e18))
    elif sort == "price_high":
        results.sort(key=lambda p: -(p.discounted_price or 0))
    elif sort == "nearest":
        results.sort(key=lambda p: (p.distance_km if p.distance_km is not None else 1e9))
    elif sort == "rating":
        results.sort(key=lambda p: -(p.rating_average or 0))
    else:  # relevance: nearer + higher rated first
        results.sort(key=lambda p: (
            (p.distance_km if p.distance_km is not None else 1e9) - (p.rating_average or 0) * 2
        ))

    return results[:limit]


def compare_product(name, lat=None, lon=None, radius_km=10.0):
    """Same/similar product name across multiple shops for price comparison."""
    return search_products(name, lat=lat, lon=lon, radius_km=radius_km, sort="price_low")


def search_services(query, lat=None, lon=None, radius_km=5.0, limit=100):
    """Also matches the shop's category name (e.g. "Mechanic", "Tailor") so
    "mechanic near me" finds services like "Bike Servicing" / "Puncture
    Repair" at a shop categorized as Mechanic, even though neither service
    name literally says "mechanic" (doc #57 category/service intent)."""
    q = (
        Service.query.join(Shop, Service.shop_id == Shop.id)
        .outerjoin(Category, Shop.category_id == Category.id)
        .filter(Shop.verification_status == VerificationStatus.APPROVED)
    )
    if query:
        condition = _tokens_filter([Service.name, Service.description, Category.name], query)
        if condition is not None:
            q = q.filter(condition)
    services = q.limit(500).all()

    results = []
    for s in services:
        shop = s.shop
        distance = haversine_km(lat, lon, shop.latitude, shop.longitude) if lat is not None else None
        if lat is not None and radius_km and distance is not None and distance > radius_km:
            continue
        s.distance_km = distance
        results.append(s)

    results.sort(key=lambda s: (s.distance_km if s.distance_km is not None else 1e9))
    return results[:limit]
