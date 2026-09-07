"""Normalizes noisy bank descriptions into a clean merchant name, preserving the original text."""
import re

_NOISE_PATTERNS = [
    r"^UPI[-/]", r"^NEFT[-/]", r"^IMPS[-/]", r"^RTGS[-/]", r"^POS\s+",
    r"\*\d+.*$", r"\d{6,}", r"[-/]\d{2,}$", r"@[\w.]+", r"\bIN$", r"\bLTD\b", r"\bPVT\b",
]

_KNOWN_MERCHANTS = {
    "SWIGGY": "Swiggy", "ZOMATO": "Zomato", "AMAZON": "Amazon", "AMZN": "Amazon",
    "FLIPKART": "Flipkart", "MYNTRA": "Myntra", "NETFLIX": "Netflix", "SPOTIFY": "Spotify",
    "UBER": "Uber", "OLA": "Ola", "IRCTC": "IRCTC", "BIGBASKET": "BigBasket",
    "AIRTEL": "Airtel", "JIO": "Jio", "VODAFONE": "Vodafone Idea", "PAYTM": "Paytm",
    "PHONEPE": "PhonePe", "GOOGLEPAY": "Google Pay", "STARBUCKS": "Starbucks",
    "DOMINOS": "Domino's", "MCDONALD": "McDonald's",
}


def _is_reference_token(word: str) -> bool:
    """True for hash/reference-code-like tokens (e.g. 'APLAPd838b9a8d7e874c81') that bank exports
    embed in transaction references -- these should never end up looking like a merchant name."""
    if len(word) < 8:
        return False
    has_digit = any(c.isdigit() for c in word)
    has_alpha = any(c.isalpha() for c in word)
    return has_digit and has_alpha


def normalize_merchant(description: str) -> str:
    text = (description or "").upper()
    for key, name in _KNOWN_MERCHANTS.items():
        if key in text:
            return name

    cleaned = text
    for pattern in _NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    cleaned = re.sub(r"[^A-Z0-9 &]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    words = [w for w in cleaned.split(" ") if (len(w) > 1 or w.isalpha()) and not _is_reference_token(w)]
    if not words:
        return description.strip()[:60] or "Unknown"
    return " ".join(w.capitalize() for w in words[:4])


def looks_like_garbage_merchant(name: str) -> bool:
    """Heuristic used to decide whether a merchant name needs an AI cleanup pass: catches
    reference-code fragments that survived normalize_merchant's regex-only pass, e.g. because
    they were split across word boundaries in a way the noise patterns didn't anticipate."""
    if not name or name.strip().lower() in ("unknown", ""):
        return True
    words = name.split()
    if not words:
        return True
    if any(_is_reference_token(w.upper()) for w in words):
        return True
    # Mostly-digit or mostly-non-alphabetic content isn't a real merchant/person name.
    alpha_chars = sum(c.isalpha() for c in name)
    if alpha_chars < max(3, len(name) * 0.4):
        return True
    return False


def normalize_description(description: str) -> str:
    text = re.sub(r"\s+", " ", (description or "").strip())
    return text
