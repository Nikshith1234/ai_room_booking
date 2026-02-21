"""
rasa_service.py - The Ears
Extracts structured booking data from natural language email text.
Uses Claude AI as primary parser with regex as fallback.

Year logic:
  - If user writes "22 March" or "March 22" with no year,
    we assume the CURRENT year (e.g. 2026).
  - If that date has already passed, we assume NEXT year.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger("BookingParser")

MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

ROOM_TYPE_MAP = {
    "deluxe": "Deluxe",
    "suite": "Suite",
    "premium suite": "Premium Suite",
    "standard": "Standard",
    "single": "Standard",
    "double": "Deluxe",
    "twin": "Standard",
    "family": "Family",
    "presidential": "Presidential Suite",
    "presidential suite": "Presidential Suite",
    "executive": "Executive Suite",
    "penthouse": "Penthouse",
    "sea view": "Deluxe Sea View Room",
    "beach": "Deluxe Sea View Room",
}


class BookingParser:
    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.api_key = anthropic_api_key
        self._client = None

        if anthropic_api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=anthropic_api_key)
                logger.info("Claude AI parser initialized.")
            except ImportError:
                logger.warning("anthropic package not found. Using regex-only parsing.")

    def extract_booking_info(self, email_body: str, sender_name: str = "", sender_email: str = "") -> Dict:
        """
        Extract booking details from email body.
        Tries Claude AI first, falls back to regex.
        """
        result = None

        if self._client:
            try:
                result = self._parse_with_claude(email_body, sender_name)
                logger.info("Used Claude AI for parsing.")
            except Exception as e:
                logger.warning(f"Claude parsing failed ({e}), falling back to regex.")

        if not result:
            result = self._parse_with_regex(email_body)
            logger.info("Used regex for parsing.")

        # Apply defaults
        if not result.get("guest_name"):
            result["guest_name"] = sender_name or sender_email.split("@")[0]

        result.setdefault("num_adults", 1)
        result.setdefault("num_children", 0)

        # Ensure year is set on dates (never leave year as None or current year if past)
        for key in ("check_in", "check_out"):
            if result.get(key):
                result[key] = self._ensure_year(result[key])

        logger.info(f"Final parsed details: {result}")
        return result

    # ── Claude AI Parsing ────────────────────────────────────────────────────
    def _parse_with_claude(self, email_body: str, sender_name: str) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year

        prompt = f"""Extract hotel booking details from this email.
Today's date is {today}. Current year is {current_year}.

EMAIL:
{email_body}

Return ONLY valid JSON with these exact keys (null for missing):
{{
  "guest_name": "string or null",
  "check_in": "YYYY-MM-DD or null",
  "check_out": "YYYY-MM-DD or null",
  "room_type": "one of: Standard, Deluxe, Suite, Premium Suite, Family, Executive Suite, Presidential Suite, Penthouse, Deluxe Sea View Room, or null",
  "num_adults": integer,
  "num_children": integer
}}

IMPORTANT RULES:
- If user writes "22 March" or "March 22" with NO year, assume year {current_year}
- If that date is already past, assume year {current_year + 1}
- Resolve "tomorrow" relative to today ({today})
- Default num_adults=1, num_children=0 if not mentioned
- If no guest name found, use "{sender_name}"
- Return ONLY the JSON object, no other text"""

        response = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(raw)

        for date_key in ("check_in", "check_out"):
            if parsed.get(date_key):
                parsed[date_key] = self._normalize_date(parsed[date_key])

        return parsed

    # ── Regex Parsing ────────────────────────────────────────────────────────
    def _parse_with_regex(self, text: str) -> Dict:
        return {
            "guest_name": self._extract_name(text),
            "check_in":   self._extract_date(text, is_checkin=True),
            "check_out":  self._extract_date(text, is_checkin=False),
            "room_type":  self._extract_room_type(text.lower()),
            "num_adults": self._extract_number(text.lower(), r"adult"),
            "num_children": self._extract_number(text.lower(), r"child(?:ren)?|kid"),
        }

    def _extract_name(self, text: str) -> Optional[str]:
        patterns = [
            r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"(?:booking for|guest(?:\s*name)?[:\s]+)([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            r"^(?:Hi|Hello|Dear)[,\s]+(?:I am|I'm)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str, is_checkin: bool) -> Optional[str]:
        today = datetime.now()
        current_year = today.year

        # "tomorrow"
        if is_checkin and re.search(r"\btomorrow\b", text, re.IGNORECASE):
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")

        # ISO: 2026-03-22
        iso_matches = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if len(iso_matches) >= 2:
            return iso_matches[0] if is_checkin else iso_matches[1]
        elif len(iso_matches) == 1 and is_checkin:
            return iso_matches[0]

        # Natural language dates: "22nd March", "March 22", "22 March 2026"
        ordinal  = r"\b(\d{1,2})(?:st|nd|rd|th)?"
        month_pat = "(" + "|".join(MONTH_MAP.keys()) + ")"
        year_pat  = r"(?:,?\s*(\d{4}))?"

        date_patterns = [
            rf"{ordinal}\s+{month_pat}\s*{year_pat}",   # 22nd March 2026
            rf"{month_pat}\s+{ordinal}[,\s]*{year_pat}", # March 22, 2026
        ]

        all_dates = []
        for pat in date_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                groups = [g for g in m.groups() if g]
                day = month = year = None
                for g in groups:
                    g_lower = g.lower()
                    if g_lower in MONTH_MAP:
                        month = MONTH_MAP[g_lower]
                    elif g.isdigit() and len(g) == 4:
                        year = int(g)
                    elif g.isdigit():
                        day = int(g)

                if day and month:
                    # If no year given → assume current year
                    if not year:
                        year = current_year
                    try:
                        dt = datetime(year, month, day)
                        # If date already passed this year, push to next year
                        if dt.date() < today.date() and year == current_year:
                            dt = datetime(current_year + 1, month, day)
                        all_dates.append((m.start(), dt.strftime("%Y-%m-%d")))
                    except ValueError:
                        pass

        if all_dates:
            all_dates.sort(key=lambda x: x[0])
            if is_checkin:
                return all_dates[0][1]
            else:
                return all_dates[1][1] if len(all_dates) > 1 else None

        return None

    def _extract_room_type(self, text: str) -> Optional[str]:
        # Check multi-word matches first (longer = more specific)
        for keyword in sorted(ROOM_TYPE_MAP.keys(), key=len, reverse=True):
            if keyword in text:
                return ROOM_TYPE_MAP[keyword]
        return None

    def _extract_number(self, text: str, keyword_pattern: str) -> int:
        word_numbers = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        pattern = rf"(\d+|{'|'.join(word_numbers.keys())})\s+(?:{keyword_pattern})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).lower()
            return word_numbers.get(val, int(val) if val.isdigit() else 1)

        pattern2 = rf"(?:{keyword_pattern})[:\s]+(\d+)"
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            return int(match2.group(1))
        return 0

    @staticmethod
    def _ensure_year(date_str: str) -> str:
        """Make sure a YYYY-MM-DD date has a proper year (not 0001 or past)."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now()
            # If year looks wrong (e.g. 0001), replace with current year
            if dt.year < 2020:
                dt = dt.replace(year=today.year)
                if dt.date() < today.date():
                    dt = dt.replace(year=today.year + 1)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return date_str

    @staticmethod
    def _normalize_date(date_str: str) -> Optional[str]:
        """Ensure date is YYYY-MM-DD format."""
        if not date_str:
            return None
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str