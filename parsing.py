"""Turn a free-text message into individual errand items.

Two jobs:
  1. split a message into separate items and label each with a category
  2. pull out a deadline if the message mentions a time
"""

import re
from datetime import datetime, timedelta

from dateparser.search import search_dates

GROCERIES = {
    "milk", "eggs", "egg", "bread", "butter", "cheese", "rice", "pasta",
    "flour", "sugar", "salt", "oil", "coffee", "tea", "juice", "water",
    "yogurt", "yoghurt", "cereal", "snacks", "chocolate", "chicken", "beef",
    "fish", "meat", "vegetables", "veg", "fruit", "apples", "bananas",
    "oranges", "tomatoes", "onions", "potatoes", "lettuce", "groceries",
    "grocery", "supermarket", "soap", "shampoo", "toothpaste",
}

PHARMACY = {
    "medicine", "medication", "meds", "prescription", "pharmacy", "chemist",
    "drugstore", "painkillers", "paracetamol", "panadol", "ibuprofen",
    "aspirin", "antibiotics", "vitamins", "vitamin", "inhaler", "bandage",
    "plaster", "plasters", "syrup", "tablets", "refill",
}

# Words that make a dateparser match trustworthy even with no digits in it.
TIME_WORDS = {
    "today", "tonight", "tomorrow", "morning", "afternoon", "evening",
    "night", "noon", "midnight", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "sunday", "weekend", "week",
}

# When a phrase names a part of the day but no clock time, assume this time.
# Matched on word boundaries: "night" must not fire inside "tonight", and
# "noon" must not fire inside "afternoon".
DAYPART_TIMES = {
    "morning": (9, 0),
    "noon": (12, 0),
    "afternoon": (14, 0),
    "evening": (18, 0),
    "tonight": (20, 0),
    "night": (20, 0),
    "midnight": (23, 59),
}

DAYPART_WORDS = "|".join(DAYPART_TIMES)

# dateparser matches "tomorrow" but drops the "morning" after it, so we
# re-attach a daypart word that immediately follows the matched phrase.
TRAILING_DAYPART_RE = re.compile(rf"\s+(?:{DAYPART_WORDS})\b", re.IGNORECASE)

# dateparser does not recognise "tonight" or "this evening" at all.
BARE_DAYPART_RE = re.compile(
    rf"\b(?:(this|tomorrow)\s+)?({DAYPART_WORDS})\b", re.IGNORECASE
)

# Split on commas, semicolons, newlines, "and", "then", "&", "plus".
SPLIT_RE = re.compile(r",|;|\n|\+|&|\bthen\b|\band\b|\bplus\b", re.IGNORECASE)

# Filler that adds nothing once the item stands alone.
LEAD_FILLER_RE = re.compile(
    r"^(?:please\s+|can\s+you\s+|could\s+you\s+|i\s+(?:need|have|want|gotta|must)\s+to\s+"
    r"|i\s+need\s+|remind\s+me\s+to\s+|remember\s+to\s+|dont\s+forget\s+to\s+"
    r"|don't\s+forget\s+to\s+|also\s+|to\s+)+",
    re.IGNORECASE,
)

# Dangling prepositions left behind after a deadline phrase is removed.
TRAIL_PREP_RE = re.compile(
    r"\s*\b(?:before|by|at|on|until|till|due|in|this|next)\b\s*$", re.IGNORECASE
)


def categorize(item):
    """Label an item by keyword match. Anything unmatched is a generic errand."""
    words = set(re.findall(r"[a-z']+", item.lower()))
    if words & PHARMACY:
        return "pharmacy"
    if words & GROCERIES:
        return "groceries"
    return "errand"


def _looks_like_time(phrase):
    """Guard against dateparser matching ordinary words as dates."""
    if any(ch.isdigit() for ch in phrase):
        return True
    return bool(set(re.findall(r"[a-z]+", phrase.lower())) & TIME_WORDS)


def _daypart_time(phrase):
    """The (hour, minute) a daypart word implies, or None if there is none."""
    for word, hm in DAYPART_TIMES.items():
        if re.search(rf"\b{word}\b", phrase, re.IGNORECASE):
            return hm
    return None


def _expand_daypart(text, phrase):
    """Re-attach a daypart word that dateparser left off the end of a match."""
    start = text.lower().find(phrase.lower())
    if start == -1:
        return phrase
    end = start + len(phrase)
    trailing = TRAILING_DAYPART_RE.match(text, end)
    return text[start:trailing.end()] if trailing else phrase


def _bare_daypart(text, now):
    """Handle 'tonight' / 'this evening', which dateparser does not parse."""
    match = BARE_DAYPART_RE.search(text)
    if not match:
        return None
    hour, minute = DAYPART_TIMES[match.group(2).lower()]
    dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if (match.group(1) or "").lower() == "tomorrow":
        dt += timedelta(days=1)
    return dt, match.group(0)


def extract_deadline(text, now=None):
    """Find a deadline in `text`.

    Returns (deadline_or_None, text_with_the_time_phrase_removed).
    """
    now = now or datetime.now()
    try:
        found = search_dates(
            text,
            languages=["en"],
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now,
                "RETURN_AS_TIMEZONE_AWARE": False,
            },
        )
    except Exception:  # dateparser can throw on odd input; a missed deadline is fine
        found = None

    result = None
    for phrase, dt in found or []:
        if not _looks_like_time(phrase):
            continue

        phrase = _expand_daypart(text, phrase)

        # No clock time in the phrase, so decide the hour ourselves:
        # "tomorrow morning" -> 09:00, a bare "today" -> end of that day.
        if not any(ch.isdigit() for ch in phrase):
            hour, minute = _daypart_time(phrase) or (23, 59)
            dt = dt.replace(hour=hour, minute=minute)

        dt = dt.replace(second=0, microsecond=0)
        # PREFER_DATES_FROM can still land in the past once we force the hour.
        if dt < now:
            dt += timedelta(days=1)
        result = (dt, phrase)
        break

    if result is None:
        result = _bare_daypart(text, now)
        if result is None:
            return None, text
        dt, phrase = result
        # "tonight" said at 22:00 is still tonight, not tomorrow night.
        result = (max(dt, now.replace(hour=23, minute=59, second=0, microsecond=0))
                  if dt < now else dt, phrase)

    dt, phrase = result
    cleaned = re.sub(re.escape(phrase), " ", text, count=1, flags=re.IGNORECASE)
    cleaned = TRAIL_PREP_RE.sub("", re.sub(r"\s{2,}", " ", cleaned).strip())
    return dt, cleaned.strip()


def parse_message(text, now=None):
    """Split a message into items, each with a category and optional deadline.

    A time mentioned anywhere in the message applies to every item from that
    message unless an item names its own time.
    """
    now = now or datetime.now()

    # A message-level deadline ("...before 6pm" at the end) covers the whole trip.
    message_deadline, _ = extract_deadline(text, now)

    items = []
    for chunk in SPLIT_RE.split(text):
        chunk = chunk.strip()
        if not chunk:
            continue

        own_deadline, cleaned = extract_deadline(chunk, now)
        cleaned = LEAD_FILLER_RE.sub("", cleaned).strip(" .!-–—:")
        if not cleaned:
            continue

        items.append(
            {
                "text": cleaned,
                "category": categorize(cleaned),
                "deadline": own_deadline or message_deadline,
            }
        )
    return items
