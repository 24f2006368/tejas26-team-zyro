"""Optional AI features (doc #55/#76/#77/#94). Must never be required for
core functionality — every function degrades gracefully when AI_ENABLED is
False (no API key configured), which is the default for this prototype."""
from flask import current_app


def is_enabled():
    return current_app.config.get("AI_ENABLED", False)


def interpret_search_query(text):
    """Very small rule-based fallback stand-in for an LLM-based interpreter.
    Real integration point: call an external AI API here when enabled."""
    text_lower = (text or "").lower()
    cheap = any(w in text_lower for w in ["cheap", "sasta", "low price", "budget"])
    near = "near me" in text_lower or "nearby" in text_lower or "nearby" in text_lower
    cleaned = text_lower
    for w in ["near me", "nearby", "cheap", "sasta", "chahiye", "please"]:
        cleaned = cleaned.replace(w, "")
    return {
        "cleaned_query": cleaned.strip() or text,
        "prefer_low_price": cheap,
        "location_scoped": near,
        "ai_used": is_enabled(),
    }


def suggest_product_from_image(image_path):
    """Stub for AI-assisted product entry (doc #55/#78). Returns None when
    AI is not configured so the merchant simply falls back to manual entry."""
    if not is_enabled():
        return None
    # Real implementation would call an external vision API here.
    return None
