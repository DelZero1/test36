import re
from datetime import datetime, timezone

URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+|\b[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/\S*)?", re.IGNORECASE)
HANDLE_PATTERN = re.compile(r"(?<!\w)@(?:[a-z0-9_]{3,})", re.IGNORECASE)

GREETING_PHRASES = {
    "hi",
    "hello",
    "hey",
    "yo",
    "sup",
    "gm",
    "gn",
    "good morning",
    "good night",
    "poz",
    "pozz",
    "bok",
    "ej",
    "cao",
    "ћао",
}
PROMO_KEYWORDS = {
    "airdrop",
    "bonus",
    "buy",
    "call",
    "channel",
    "click",
    "deal",
    "drop",
    "earn",
    "free",
    "giveaway",
    "guaranteed",
    "invite",
    "join",
    "listing",
    "moon",
    "offer",
    "presale",
    "profit",
    "promo",
    "pump",
    "ref",
    "referral",
    "reward",
    "sale",
    "seed phrase",
    "signal",
    "signals",
    "staking",
    "subscribe",
    "trade with me",
    "whitelist",
}
CLICKBAIT_KEYWORDS = {
    "100x",
    "act now",
    "breaking",
    "don't miss",
    "easy money",
    "limited time",
    "must see",
    "urgent",
}
BC2_KEYWORDS = {
    "bc2",
    "bitcoin ii",
    "bitcoin-ii",
    "bitcoin ii",
    "bitcoin-ii.org",
    "bitcoinii",
    "explorer",
    "nodemap",
    "nonkyc",
    "coinex",
    "rabid-rabbit",
    "rabid rabbit",
    "nestex",
    "wallet",
    "mining",
    "transaction",
    "transactions",
    "block",
    "node",
    "nodes",
}


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def safe_message_text(text: str | None, caption: str | None) -> str:
    value = text or caption or ""
    return value.strip()


def should_prefilter_classify_message(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    if not normalized:
        return False

    if len(normalized) <= 3:
        return False

    words = re.findall(r"[\w@.-]+", normalized)
    if not words:
        return False

    if normalized in GREETING_PHRASES:
        return False

    if len(words) <= 4 and not any(char.isdigit() for char in normalized):
        if not URL_PATTERN.search(normalized) and not HANDLE_PATTERN.search(normalized):
            if not any(keyword in normalized for keyword in PROMO_KEYWORDS | CLICKBAIT_KEYWORDS):
                return False

    has_link = URL_PATTERN.search(normalized) is not None
    has_handle = HANDLE_PATTERN.search(normalized) is not None
    has_promo_language = any(keyword in normalized for keyword in PROMO_KEYWORDS)
    has_clickbait = any(keyword in normalized for keyword in CLICKBAIT_KEYWORDS)
    mentions_bc2 = any(keyword in normalized for keyword in BC2_KEYWORDS)
    long_enough_for_review = len(words) >= 5

    if has_link or has_handle or has_promo_language or has_clickbait:
        return True

    if long_enough_for_review and not mentions_bc2:
        return True

    return False


def build_warning_message(reason: str, classification: str) -> str:
    short_reason = " ".join(reason.split()).strip(" .,!?")
    if not short_reason:
        short_reason = "ovo djeluje nepovezano s BC2 temom"

    if classification == "SPAM":
        return f"⚠️ Ovo izgleda kao spam/promo ({short_reason}). Drži se BC2 teme."
    if "link" in short_reason.lower():
        return f"⚠️ Link djeluje nepovezano s temom grupe ({short_reason}). Molim bez promocije sa strane."
    return f"⚠️ Ovo izgleda sumnjivo ({short_reason}). Piši vezano za BC2."
