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

    words = [w for w in cleaned.split(" ") if len(w) > 1 or w.isalpha()]
    if not words:
        return description.strip()[:60] or "Unknown"
    return " ".join(w.capitalize() for w in words[:4])


def normalize_description(description: str) -> str:
    text = re.sub(r"\s+", " ", (description or "").strip())
    return text
