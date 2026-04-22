"""
Resolve plain-text location names (countries, cities, regions) to IATA airport codes.

Usage:
    from app.utils.location_resolver import resolve_location

    resolve_location("Canada")          # ["YYZ", "YVR", "YEG", "YYC", "YHZ", "YUL", "YOW"]
    resolve_location("Vietnam")         # ["SGN", "HAN", "DAD"]
    resolve_location("Tokyo")           # ["NRT", "HND"]
    resolve_location("TYO, SHA")        # ["TYO", "SHA"]   (raw IATA pass-through)
    resolve_location("Canada, USA")     # merged list of both
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Master lookup — lowercase key → list of major IATA codes
# ---------------------------------------------------------------------------
_MAP: dict[str, list[str]] = {
    # ── Canada ──────────────────────────────────────────────────────────────
    "canada": ["YYZ", "YVR", "YEG", "YYC", "YHZ", "YUL", "YOW"],
    "toronto": ["YYZ"],
    "vancouver": ["YVR"],
    "edmonton": ["YEG"],
    "calgary": ["YYC"],
    "halifax": ["YHZ"],
    "montreal": ["YUL"],
    "ottawa": ["YOW"],
    "winnipeg": ["YWG"],
    "victoria": ["YYJ"],
    "kelowna": ["YLW"],

    # ── Vietnam ──────────────────────────────────────────────────────────────
    "vietnam": ["SGN", "HAN", "DAD"],
    "viet nam": ["SGN", "HAN", "DAD"],
    "ho chi minh": ["SGN"],
    "ho chi minh city": ["SGN"],
    "saigon": ["SGN"],
    "hcmc": ["SGN"],
    "hanoi": ["HAN"],
    "ha noi": ["HAN"],
    "da nang": ["DAD"],
    "danang": ["DAD"],
    "phu quoc": ["PQC"],
    "nha trang": ["CXR"],
    "hue": ["HUI"],

    # ── Japan ────────────────────────────────────────────────────────────────
    "japan": ["NRT", "HND", "KIX", "NGO", "FUK", "CTS"],
    "tokyo": ["NRT", "HND"],
    "osaka": ["KIX"],
    "kyoto": ["KIX"],
    "nagoya": ["NGO"],
    "fukuoka": ["FUK"],
    "sapporo": ["CTS"],
    "okinawa": ["OKA"],
    "hiroshima": ["HIJ"],

    # ── China ────────────────────────────────────────────────────────────────
    "china": ["PEK", "PVG", "CAN", "SHA", "CTU", "XIY"],
    "beijing": ["PEK"],
    "shanghai": ["PVG", "SHA"],
    "guangzhou": ["CAN"],
    "shenzhen": ["SZX"],
    "chengdu": ["CTU"],
    "xian": ["XIY"],
    "xi'an": ["XIY"],
    "chongqing": ["CKG"],
    "wuhan": ["WUH"],
    "kunming": ["KMG"],

    # ── South Korea ──────────────────────────────────────────────────────────
    "south korea": ["ICN", "GMP", "PUS"],
    "korea": ["ICN", "GMP", "PUS"],
    "seoul": ["ICN", "GMP"],
    "busan": ["PUS"],
    "jeju": ["CJU"],

    # ── Thailand ─────────────────────────────────────────────────────────────
    "thailand": ["BKK", "DMK", "HKT", "CNX", "USM"],
    "bangkok": ["BKK", "DMK"],
    "phuket": ["HKT"],
    "chiang mai": ["CNX"],
    "chiangmai": ["CNX"],
    "koh samui": ["USM"],
    "samui": ["USM"],

    # ── Indonesia ────────────────────────────────────────────────────────────
    "indonesia": ["CGK", "DPS", "SUB", "LOP"],
    "bali": ["DPS"],
    "jakarta": ["CGK"],
    "surabaya": ["SUB"],
    "lombok": ["LOP"],
    "yogyakarta": ["JOG"],

    # ── Malaysia ─────────────────────────────────────────────────────────────
    "malaysia": ["KUL", "PEN", "BKI", "KCH"],
    "kuala lumpur": ["KUL"],
    "kl": ["KUL"],
    "penang": ["PEN"],
    "kota kinabalu": ["BKI"],
    "kuching": ["KCH"],
    "langkawi": ["LGK"],

    # ── Singapore ────────────────────────────────────────────────────────────
    "singapore": ["SIN"],

    # ── Philippines ──────────────────────────────────────────────────────────
    "philippines": ["MNL", "CEB", "DVO"],
    "manila": ["MNL"],
    "cebu": ["CEB"],
    "davao": ["DVO"],
    "boracay": ["MPH"],
    "palawan": ["PPS"],

    # ── India ────────────────────────────────────────────────────────────────
    "india": ["DEL", "BOM", "MAA", "BLR", "CCU", "HYD", "COK"],
    "delhi": ["DEL"],
    "new delhi": ["DEL"],
    "mumbai": ["BOM"],
    "bombay": ["BOM"],
    "bangalore": ["BLR"],
    "bengaluru": ["BLR"],
    "chennai": ["MAA"],
    "madras": ["MAA"],
    "kolkata": ["CCU"],
    "calcutta": ["CCU"],
    "hyderabad": ["HYD"],
    "kochi": ["COK"],
    "cochin": ["COK"],
    "goa": ["GOI"],
    "ahmedabad": ["AMD"],
    "amdavad": ["AMD"],
    "surat": ["STV"],
    "pune": ["PNQ"],
    "poona": ["PNQ"],
    "jaipur": ["JAI"],
    "lucknow": ["LKO"],
    "bhopal": ["BHO"],
    "nagpur": ["NAG"],
    "patna": ["PAT"],
    "varanasi": ["VNS"],
    "bhubaneswar": ["BBI"],
    "amritsar": ["ATQ"],
    "chandigarh": ["IXC"],
    "coimbatore": ["CJB"],
    "trichy": ["TRZ"],
    "tiruchirappalli": ["TRZ"],
    "mangalore": ["IXE"],
    "vizag": ["VTZ"],
    "visakhapatnam": ["VTZ"],
    "indore": ["IDR"],
    "udaipur": ["UDR"],
    "jodhpur": ["JDH"],
    "jammu": ["IXJ"],
    "srinagar": ["SXR"],
    "port blair": ["IXZ"],

    # ── Sri Lanka ────────────────────────────────────────────────────────────
    "sri lanka": ["CMB"],
    "colombo": ["CMB"],

    # ── Nepal ────────────────────────────────────────────────────────────────
    "nepal": ["KTM"],
    "kathmandu": ["KTM"],

    # ── Maldives ─────────────────────────────────────────────────────────────
    "maldives": ["MLE"],
    "male": ["MLE"],
    "malé": ["MLE"],

    # ── Hong Kong ────────────────────────────────────────────────────────────
    "hong kong": ["HKG"],

    # ── Taiwan ───────────────────────────────────────────────────────────────
    "taiwan": ["TPE", "KHH"],
    "taipei": ["TPE"],
    "kaohsiung": ["KHH"],

    # ── UAE ──────────────────────────────────────────────────────────────────
    "uae": ["DXB", "AUH", "SHJ"],
    "united arab emirates": ["DXB", "AUH", "SHJ"],
    "dubai": ["DXB"],
    "abu dhabi": ["AUH"],
    "sharjah": ["SHJ"],

    # ── Cambodia ─────────────────────────────────────────────────────────────
    "cambodia": ["PNH", "REP"],
    "phnom penh": ["PNH"],
    "siem reap": ["REP"],
    "angkor": ["REP"],

    # ── Myanmar ──────────────────────────────────────────────────────────────
    "myanmar": ["RGN", "MDL"],
    "burma": ["RGN", "MDL"],
    "yangon": ["RGN"],
    "rangoon": ["RGN"],
    "mandalay": ["MDL"],

    # ── Laos ─────────────────────────────────────────────────────────────────
    "laos": ["VTE", "LPQ"],
    "vientiane": ["VTE"],
    "luang prabang": ["LPQ"],

    # ── Bangladesh ───────────────────────────────────────────────────────────
    "bangladesh": ["DAC"],
    "dhaka": ["DAC"],

    # ── Pakistan ─────────────────────────────────────────────────────────────
    "pakistan": ["KHI", "LHE", "ISB"],
    "karachi": ["KHI"],
    "lahore": ["LHE"],
    "islamabad": ["ISB"],

    # ── UK ───────────────────────────────────────────────────────────────────
    "uk": ["LHR", "LGW", "MAN", "EDI", "GLA", "BHX"],
    "united kingdom": ["LHR", "LGW", "MAN", "EDI", "GLA", "BHX"],
    "britain": ["LHR", "LGW", "MAN", "EDI"],
    "great britain": ["LHR", "LGW", "MAN", "EDI"],
    "england": ["LHR", "LGW", "MAN", "BHX"],
    "london": ["LHR", "LGW"],
    "manchester": ["MAN"],
    "edinburgh": ["EDI"],
    "glasgow": ["GLA"],
    "birmingham": ["BHX"],

    # ── France ───────────────────────────────────────────────────────────────
    "france": ["CDG", "ORY", "NCE", "LYS", "MRS"],
    "paris": ["CDG", "ORY"],
    "nice": ["NCE"],
    "lyon": ["LYS"],
    "marseille": ["MRS"],

    # ── Germany ──────────────────────────────────────────────────────────────
    "germany": ["FRA", "MUC", "BER", "DUS", "HAM", "STR"],
    "frankfurt": ["FRA"],
    "munich": ["MUC"],
    "münchen": ["MUC"],
    "berlin": ["BER"],
    "dusseldorf": ["DUS"],
    "düsseldorf": ["DUS"],
    "hamburg": ["HAM"],
    "stuttgart": ["STR"],
    "cologne": ["CGN"],
    "köln": ["CGN"],

    # ── Italy ────────────────────────────────────────────────────────────────
    "italy": ["FCO", "MXP", "VCE", "NAP", "PMO", "BLQ"],
    "rome": ["FCO"],
    "milan": ["MXP", "LIN"],
    "venice": ["VCE"],
    "naples": ["NAP"],
    "palermo": ["PMO"],
    "bologna": ["BLQ"],
    "florence": ["FLR"],

    # ── Spain ────────────────────────────────────────────────────────────────
    "spain": ["MAD", "BCN", "AGP", "PMI", "SVQ", "VLC"],
    "madrid": ["MAD"],
    "barcelona": ["BCN"],
    "malaga": ["AGP"],
    "málaga": ["AGP"],
    "ibiza": ["IBZ"],
    "majorca": ["PMI"],
    "mallorca": ["PMI"],
    "seville": ["SVQ"],
    "sevilla": ["SVQ"],
    "valencia": ["VLC"],

    # ── Portugal ─────────────────────────────────────────────────────────────
    "portugal": ["LIS", "OPO", "FAO"],
    "lisbon": ["LIS"],
    "porto": ["OPO"],
    "faro": ["FAO"],
    "algarve": ["FAO"],

    # ── Greece ───────────────────────────────────────────────────────────────
    "greece": ["ATH", "SKG", "HER", "JMK", "JTR", "CFU"],
    "athens": ["ATH"],
    "thessaloniki": ["SKG"],
    "crete": ["HER"],
    "heraklion": ["HER"],
    "mykonos": ["JMK"],
    "santorini": ["JTR"],
    "corfu": ["CFU"],

    # ── Turkey ───────────────────────────────────────────────────────────────
    "turkey": ["IST", "SAW", "AYT", "ADB", "DLM"],
    "türkiye": ["IST", "SAW", "AYT", "ADB"],
    "istanbul": ["IST", "SAW"],
    "antalya": ["AYT"],
    "izmir": ["ADB"],
    "bodrum": ["BJV"],
    "dalaman": ["DLM"],

    # ── Netherlands ──────────────────────────────────────────────────────────
    "netherlands": ["AMS", "EIN"],
    "holland": ["AMS", "EIN"],
    "amsterdam": ["AMS"],

    # ── Switzerland ──────────────────────────────────────────────────────────
    "switzerland": ["ZRH", "GVA", "BSL"],
    "zurich": ["ZRH"],
    "zürich": ["ZRH"],
    "geneva": ["GVA"],
    "basel": ["BSL"],

    # ── Austria ──────────────────────────────────────────────────────────────
    "austria": ["VIE", "GRZ", "SZG"],
    "vienna": ["VIE"],
    "wien": ["VIE"],
    "graz": ["GRZ"],
    "salzburg": ["SZG"],

    # ── Belgium ──────────────────────────────────────────────────────────────
    "belgium": ["BRU", "CRL"],
    "brussels": ["BRU"],
    "bruxelles": ["BRU"],

    # ── Sweden ───────────────────────────────────────────────────────────────
    "sweden": ["ARN", "GOT", "MMX"],
    "stockholm": ["ARN"],
    "gothenburg": ["GOT"],
    "malmo": ["MMX"],
    "malmö": ["MMX"],

    # ── Norway ───────────────────────────────────────────────────────────────
    "norway": ["OSL", "BGO", "TRD"],
    "oslo": ["OSL"],
    "bergen": ["BGO"],

    # ── Denmark ──────────────────────────────────────────────────────────────
    "denmark": ["CPH"],
    "copenhagen": ["CPH"],

    # ── Finland ──────────────────────────────────────────────────────────────
    "finland": ["HEL"],
    "helsinki": ["HEL"],

    # ── Poland ───────────────────────────────────────────────────────────────
    "poland": ["WAW", "KRK", "GDN"],
    "warsaw": ["WAW"],
    "krakow": ["KRK"],
    "kraków": ["KRK"],
    "gdansk": ["GDN"],
    "gdańsk": ["GDN"],

    # ── Czech Republic ───────────────────────────────────────────────────────
    "czech republic": ["PRG"],
    "czechia": ["PRG"],
    "prague": ["PRG"],

    # ── Hungary ──────────────────────────────────────────────────────────────
    "hungary": ["BUD"],
    "budapest": ["BUD"],

    # ── Croatia ──────────────────────────────────────────────────────────────
    "croatia": ["ZAG", "SPU", "DBV"],
    "zagreb": ["ZAG"],
    "split": ["SPU"],
    "dubrovnik": ["DBV"],

    # ── Ireland ──────────────────────────────────────────────────────────────
    "ireland": ["DUB", "ORK", "SNN"],
    "dublin": ["DUB"],
    "cork": ["ORK"],

    # ── Iceland ──────────────────────────────────────────────────────────────
    "iceland": ["KEF"],
    "reykjavik": ["KEF"],
    "reykjavík": ["KEF"],

    # ── Israel ───────────────────────────────────────────────────────────────
    "israel": ["TLV"],
    "tel aviv": ["TLV"],

    # ── Jordan ───────────────────────────────────────────────────────────────
    "jordan": ["AMM", "AQJ"],
    "amman": ["AMM"],
    "aqaba": ["AQJ"],

    # ── Saudi Arabia ─────────────────────────────────────────────────────────
    "saudi arabia": ["JED", "RUH", "MED"],
    "saudi": ["JED", "RUH"],
    "jeddah": ["JED"],
    "riyadh": ["RUH"],
    "medina": ["MED"],

    # ── USA ──────────────────────────────────────────────────────────────────
    "usa": ["JFK", "LAX", "ORD", "MIA", "SFO", "DFW", "ATL", "SEA", "BOS", "LAS", "DEN"],
    "us": ["JFK", "LAX", "ORD", "MIA", "SFO", "DFW", "ATL", "SEA", "BOS", "LAS", "DEN"],
    "united states": ["JFK", "LAX", "ORD", "MIA", "SFO", "DFW", "ATL", "SEA", "BOS", "LAS", "DEN"],
    "america": ["JFK", "LAX", "ORD", "MIA", "SFO", "DFW", "ATL", "SEA", "BOS", "LAS", "DEN"],
    "new york": ["JFK", "EWR"],
    "nyc": ["JFK", "EWR"],
    "los angeles": ["LAX"],
    "la": ["LAX"],
    "chicago": ["ORD", "MDW"],
    "miami": ["MIA", "FLL"],
    "san francisco": ["SFO"],
    "dallas": ["DFW"],
    "atlanta": ["ATL"],
    "seattle": ["SEA"],
    "boston": ["BOS"],
    "las vegas": ["LAS"],
    "denver": ["DEN"],
    "hawaii": ["HNL", "OGG"],
    "honolulu": ["HNL"],
    "maui": ["OGG"],
    "orlando": ["MCO"],
    "new orleans": ["MSY"],
    "phoenix": ["PHX"],
    "houston": ["IAH", "HOU"],
    "washington": ["IAD", "DCA"],
    "dc": ["IAD", "DCA"],

    # ── Mexico ───────────────────────────────────────────────────────────────
    "mexico": ["MEX", "CUN", "GDL", "MTY", "SJD", "PVR"],
    "mexico city": ["MEX"],
    "cancun": ["CUN"],
    "guadalajara": ["GDL"],
    "los cabos": ["SJD"],
    "cabo": ["SJD"],
    "cabo san lucas": ["SJD"],
    "puerto vallarta": ["PVR"],

    # ── Brazil ───────────────────────────────────────────────────────────────
    "brazil": ["GRU", "GIG", "BSB", "SSA", "REC"],
    "sao paulo": ["GRU"],
    "são paulo": ["GRU"],
    "rio de janeiro": ["GIG", "SDU"],
    "rio": ["GIG"],
    "brasilia": ["BSB"],
    "brasília": ["BSB"],

    # ── Argentina ────────────────────────────────────────────────────────────
    "argentina": ["EZE", "AEP", "COR"],
    "buenos aires": ["EZE", "AEP"],

    # ── Colombia ─────────────────────────────────────────────────────────────
    "colombia": ["BOG", "MDE", "CTG"],
    "bogota": ["BOG"],
    "bogotá": ["BOG"],
    "medellin": ["MDE"],
    "medellín": ["MDE"],
    "cartagena": ["CTG"],

    # ── Peru ─────────────────────────────────────────────────────────────────
    "peru": ["LIM", "CUZ"],
    "lima": ["LIM"],
    "cusco": ["CUZ"],
    "cuzco": ["CUZ"],
    "machu picchu": ["CUZ"],

    # ── Cuba ─────────────────────────────────────────────────────────────────
    "cuba": ["HAV", "VRA"],
    "havana": ["HAV"],
    "varadero": ["VRA"],

    # ── Dominican Republic ───────────────────────────────────────────────────
    "dominican republic": ["PUJ", "SDQ"],
    "punta cana": ["PUJ"],
    "santo domingo": ["SDQ"],

    # ── Jamaica ──────────────────────────────────────────────────────────────
    "jamaica": ["KIN", "MBJ"],
    "kingston": ["KIN"],
    "montego bay": ["MBJ"],

    # ── Australia ────────────────────────────────────────────────────────────
    "australia": ["SYD", "MEL", "BNE", "PER", "ADL", "CNS"],
    "sydney": ["SYD"],
    "melbourne": ["MEL"],
    "brisbane": ["BNE"],
    "perth": ["PER"],
    "adelaide": ["ADL"],
    "cairns": ["CNS"],
    "gold coast": ["OOL"],

    # ── New Zealand ──────────────────────────────────────────────────────────
    "new zealand": ["AKL", "CHC", "WLG", "ZQN"],
    "auckland": ["AKL"],
    "christchurch": ["CHC"],
    "wellington": ["WLG"],
    "queenstown": ["ZQN"],

    # ── Fiji ─────────────────────────────────────────────────────────────────
    "fiji": ["NAN", "SUV"],
    "nadi": ["NAN"],

    # ── South Africa ─────────────────────────────────────────────────────────
    "south africa": ["JNB", "CPT", "DUR"],
    "johannesburg": ["JNB"],
    "cape town": ["CPT"],
    "durban": ["DUR"],

    # ── Egypt ────────────────────────────────────────────────────────────────
    "egypt": ["CAI", "HRG", "SSH", "LXR"],
    "cairo": ["CAI"],
    "hurghada": ["HRG"],
    "sharm el sheikh": ["SSH"],
    "luxor": ["LXR"],

    # ── Morocco ──────────────────────────────────────────────────────────────
    "morocco": ["CMN", "RAK", "AGA", "FEZ"],
    "casablanca": ["CMN"],
    "marrakech": ["RAK"],
    "marrakesh": ["RAK"],
    "agadir": ["AGA"],
    "fez": ["FEZ"],

    # ── Kenya ────────────────────────────────────────────────────────────────
    "kenya": ["NBO", "MBA"],
    "nairobi": ["NBO"],
    "mombasa": ["MBA"],

    # ── Tanzania ─────────────────────────────────────────────────────────────
    "tanzania": ["DAR", "ZNZ", "JRO"],
    "dar es salaam": ["DAR"],
    "zanzibar": ["ZNZ"],
    "kilimanjaro": ["JRO"],

    # ── Ethiopia ─────────────────────────────────────────────────────────────
    "ethiopia": ["ADD"],
    "addis ababa": ["ADD"],

    # ── Russia ───────────────────────────────────────────────────────────────
    "russia": ["SVO", "DME", "LED", "SVX"],
    "moscow": ["SVO", "DME"],
    "saint petersburg": ["LED"],
    "st petersburg": ["LED"],
    "st. petersburg": ["LED"],
}


def resolve_location(query: str) -> list[str]:
    """
    Resolve a location string to a deduplicated list of IATA codes.

    Handles:
    - Country names:  "Canada", "Vietnam", "Japan"
    - City names:     "Tokyo", "Toronto", "London"
    - IATA codes:     "YYZ", "SGN", "NRT"
    - Comma-separated combinations: "TYO, SHA" or "Vietnam, Thailand"
    - Mixed:          "Canada, YYZ" (deduped)

    Returns an empty list if nothing matches.
    """
    parts = [p.strip() for p in query.split(",") if p.strip()]
    seen: set[str] = set()
    result: list[str] = []

    for part in parts:
        for code in _resolve_single(part):
            if code not in seen:
                seen.add(code)
                result.append(code)

    return result


def _resolve_single(query: str) -> list[str]:
    """Resolve a single location token."""
    key = query.strip().lower()

    # Direct dictionary hit
    if key in _MAP:
        return list(_MAP[key])

    # Raw IATA code pass-through (2–4 uppercase letters)
    upper = query.strip().upper()
    if 2 <= len(upper) <= 4 and upper.isalpha():
        return [upper]

    return []


def list_known_locations() -> list[str]:
    """Return all resolvable location names, sorted, for UI hints."""
    return sorted({k.title() for k in _MAP})
