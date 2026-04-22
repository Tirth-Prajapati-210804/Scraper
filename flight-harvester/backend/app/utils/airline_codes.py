from __future__ import annotations

AIRLINE_MAP: dict[str, str] = {
    # ── Full names → IATA codes ───────────────────────────────────────────────
    # Major international carriers
    "AIR INDIA": "AI",
    "AIR CANADA": "AC",
    "AIR FRANCE": "AF",
    "AIR ASIA": "AK",
    "AIRASIA": "AK",
    "AIR ARABIA": "G9",
    "AIR CHINA": "CA",
    "AIR NEW ZEALAND": "NZ",
    "ALASKA AIRLINES": "AS",
    "AMERICAN AIRLINES": "AA",
    "ANA": "NH",
    "ALL NIPPON AIRWAYS": "NH",
    "AUSTRIAN": "OS",
    "AUSTRIAN AIRLINES": "OS",
    "BANGKOK AIRWAYS": "PG",
    "BRITISH AIRWAYS": "BA",
    "CATHAY PACIFIC": "CX",
    "CHINA EASTERN": "MU",
    "CHINA SOUTHERN": "CZ",
    "DELTA": "DL",
    "DELTA AIR LINES": "DL",
    "EMIRATES": "EK",
    "ETIHAD": "EY",
    "ETIHAD AIRWAYS": "EY",
    "EVA AIR": "BR",
    "FINNAIR": "AY",
    "FLYDUBAI": "FZ",
    "GARUDA INDONESIA": "GA",
    "GULF AIR": "GF",
    "HAINAN AIRLINES": "HU",
    "HIMALAYA AIRLINES": "H9",
    "INDIGO": "6E",
    "INDONESIA AIRASIA": "QZ",
    "JAPAN AIRLINES": "JL",
    "JAPAN": "JL",
    "JET AIRWAYS": "9W",
    "JETBLUE": "B6",
    "JETBLUE AIRWAYS": "B6",
    "KENYA AIRWAYS": "KQ",
    "KLM": "KL",
    "KLM ROYAL DUTCH AIRLINES": "KL",
    "KOREAN AIR": "KE",
    "LUFTHANSA": "LH",
    "LUFTHANSANA": "LH",
    "LUTHANSA": "LH",
    "MALAYSIA AIRLINES": "MH",
    "MALAYSIA": "MH",
    "MALINDO AIR": "OD",
    "OMAN AIR": "WY",
    "PHILIPPINES AIRLINES": "PR",
    "PHILIPPINE AIRLINES": "PR",
    "QATAR AIRWAYS": "QR",
    "ROYAL JORDANIAN": "RJ",
    "SCOOT": "TR",
    "SINGAPORE AIRLINES": "SQ",
    "SRILANKAN AIRLINES": "UL",
    "SWISS": "LX",
    "SWISS INTERNATIONAL AIR LINES": "LX",
    "THAI AIRWAYS": "TG",
    "THAI AIRWAYS INTERNATIONAL": "TG",
    "THAI AIRASIA": "FD",
    "THAI LION AIR": "SL",
    "THAI SMILE": "WE",
    "TIGERAIR": "TR",
    "TURKISH AIRLINES": "TK",
    "UNITED": "UA",
    "UNITED AIRLINES": "UA",
    "VIETNAM AIRLINES": "VN",
    "VIETJET": "VJ",
    "VIETJET AIR": "VJ",
    "VIETJET AVIATION": "VJ",
    "XIAMEN AIRLINES": "MF",

    # ── IATA codes → pass through ─────────────────────────────────────────────
    "6E": "6E",   # IndiGo
    "9W": "9W",   # Jet Airways
    "AA": "AA",
    "AC": "AC",
    "AF": "AF",
    "AI": "AI",
    "AK": "AK",
    "AS": "AS",
    "AY": "AY",
    "B6": "B6",
    "BA": "BA",
    "BR": "BR",
    "CA": "CA",
    "CE": "CE",
    "CP": "CP",
    "CS": "CS",
    "CX": "CX",
    "CZ": "CZ",
    "DL": "DL",
    "EA": "EA",
    "EK": "EK",
    "EY": "EY",
    "FD": "FD",
    "FZ": "FZ",
    "G9": "G9",
    "GA": "GA",
    "GF": "GF",
    "H9": "H9",
    "HKA": "HKA",
    "HU": "HU",
    "JL": "JL",
    "KA": "KA",
    "KE": "KE",
    "KL": "KL",
    "KQ": "KQ",
    "LH": "LH",
    "LX": "LX",
    "MF": "MF",
    "MH": "MH",
    "MU": "MU",
    "NH": "NH",
    "NZ": "NZ",
    "OD": "OD",
    "OS": "OS",
    "PA": "PA",
    "PG": "PG",
    "PR": "PR",
    "QA": "QA",
    "QR": "QR",
    "QZ": "QZ",
    "RJ": "RJ",
    "SL": "SL",
    "SQ": "SQ",
    "TA": "TA",
    "TG": "TG",
    "TK": "TK",
    "TR": "TR",
    "UA": "UA",
    "UL": "UL",
    "VJ": "VJ",
    "VN": "VN",
    "WE": "WE",
    "WY": "WY",

    # ── Partial / garbled forms seen in provider responses ────────────────────
    "J A": "JL",
    "EVA A": "BR",
    "K A": "KA",
    "A F": "AF",
    "A I": "AI",
    "C A": "CA",
    "C P": "CP",
}


def normalize_airline(raw: str) -> str:
    if not raw or not raw.strip():
        return "-"
    cleaned = raw.strip().upper()

    # Exact match (handles both full names and IATA codes)
    if cleaned in AIRLINE_MAP:
        return AIRLINE_MAP[cleaned]

    # Already a short code (≤3 chars) — return as-is
    if len(cleaned) <= 3:
        return cleaned

    # Try matching the first word (e.g. "VIETJET AIR" → "VIETJET" → "VJ")
    first_word = cleaned.split()[0]
    if first_word in AIRLINE_MAP:
        return AIRLINE_MAP[first_word]

    # Try matching first two words (e.g. "MALAYSIA AIRLINES" if exact key not found)
    words = cleaned.split()
    if len(words) >= 2:
        two_words = f"{words[0]} {words[1]}"
        if two_words in AIRLINE_MAP:
            return AIRLINE_MAP[two_words]

    # Unknown airline — truncate to 10 chars to prevent garbage data in exports
    return raw.strip()[:10]
