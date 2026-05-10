import difflib
import unicodedata


COUNTRY_AIRPORTS: dict[str, list[str]] = {
    "japão": ["NRT", "HND", "KIX", "NGO", "FUK"],
    "japan": ["NRT", "HND", "KIX", "NGO", "FUK"],
    "portugal": ["LIS", "OPO"],
    "espanha": ["MAD", "BCN"],
    "frança": ["CDG", "ORY", "NCE"],
    "itália": ["FCO", "MXP", "VCE"],
    "alemanha": ["FRA", "MUC", "BER"],
    "reino unido": ["LHR", "LGW", "MAN"],
    "estados unidos": ["JFK", "LAX", "MIA", "ORD", "ATL", "DFW"],
    "eua": ["JFK", "LAX", "MIA", "ORD", "ATL", "DFW"],
    "argentina": ["EZE", "AEP"],
    "chile": ["SCL"],
    "uruguai": ["MVD"],
    "peru": ["LIM"],
    "colômbia": ["BOG"],
    "méxico": ["MEX", "CUN"],
    "brasil": ["GRU", "CGH", "VCP", "GIG", "SDU", "BSB", "SSA", "FOR", "REC", "CWB", "POA"],
    "coreia do sul": ["ICN", "GMP"],
    "china": ["PEK", "PVG", "CAN"],
    "tailândia": ["BKK", "DMK"],
    "emirados árabes": ["DXB", "AUH"],
    "turquia": ["IST"],
    "holanda": ["AMS"],
    "países baixos": ["AMS"],
}

CITY_AIRPORTS: dict[str, list[str]] = {
    "são paulo": ["GRU", "CGH", "VCP"],
    "rio de janeiro": ["GIG", "SDU"],
    "brasília": ["BSB"],
    "salvador": ["SSA"],
    "fortaleza": ["FOR"],
    "recife": ["REC"],
    "manaus": ["MAN"],
    "belém": ["BEL"],
    "curitiba": ["CWB"],
    "porto alegre": ["POA"],
    "belo horizonte": ["CNF"],
    "tóquio": ["NRT", "HND"],
    "osaka": ["KIX", "ITM"],
    "nagoya": ["NGO"],
    "fukuoka": ["FUK"],
    "sapporo": ["CTS"],
    "okinawa": ["OKA"],
    "lisboa": ["LIS"],
    "porto": ["OPO"],
    "madri": ["MAD"],
    "barcelona": ["BCN"],
    "paris": ["CDG", "ORY"],
    "londres": ["LHR", "LGW"],
    "roma": ["FCO"],
    "milão": ["MXP", "LIN"],
    "frankfurt": ["FRA"],
    "munique": ["MUC"],
    "amsterdã": ["AMS"],
    "nova york": ["JFK", "LGA", "EWR"],
    "los angeles": ["LAX"],
    "miami": ["MIA"],
    "chicago": ["ORD"],
    "buenos aires": ["EZE", "AEP"],
    "santiago": ["SCL"],
    "lima": ["LIM"],
    "cidade do méxico": ["MEX"],
    "seul": ["ICN", "GMP"],
    "pequim": ["PEK"],
    "xangai": ["PVG"],
    "bangkok": ["BKK"],
    "dubai": ["DXB"],
    "istambul": ["IST"],
}

BRAZIL_AIRPORTS: set[str] = {
    "GRU", "CGH", "VCP", "GIG", "SDU", "BSB", "SSA", "FOR", "REC",
    "CWB", "POA", "CNF", "MAN", "BEL", "FLN", "NAT", "MCZ", "VIX",
    "GYN", "CGB", "CGR", "AJU", "THE", "SLZ", "PMW", "BVB", "MCP",
    "PVH", "RBR", "MAO",
}


class LocationNotFoundError(Exception):
    pass


def _normalize(text: str) -> str:
    text = text.strip().lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _build_normalized(table: dict[str, list[str]]) -> dict[str, tuple[str, list[str]]]:
    return {_normalize(k): (k, v) for k, v in table.items()}


_CITY_NORM = _build_normalized(CITY_AIRPORTS)
_COUNTRY_NORM = _build_normalized(COUNTRY_AIRPORTS)


def resolve_location(query: str) -> tuple[list[str], str]:
    if not query or not query.strip():
        raise LocationNotFoundError("Localização vazia. Informe uma cidade, país ou IATA.")

    raw = query.strip()
    if len(raw) == 3 and raw.isalpha() and raw.isupper():
        return [raw], raw

    norm = _normalize(raw)

    if norm in _CITY_NORM:
        canonical, codes = _CITY_NORM[norm]
        return list(codes), canonical.title()

    if norm in _COUNTRY_NORM:
        canonical, codes = _COUNTRY_NORM[norm]
        return list(codes), canonical.title()

    candidates = list(_CITY_NORM.keys()) + list(_COUNTRY_NORM.keys())
    suggestions = difflib.get_close_matches(norm, candidates, n=3, cutoff=0.6)
    suggestion_text = ""
    if suggestions:
        readable = []
        for s in suggestions:
            if s in _CITY_NORM:
                readable.append(_CITY_NORM[s][0].title())
            elif s in _COUNTRY_NORM:
                readable.append(_COUNTRY_NORM[s][0].title())
        if readable:
            suggestion_text = f" Sugestões: {', '.join(readable)}."

    raise LocationNotFoundError(
        f"Localização '{query}' não encontrada no mapa interno.{suggestion_text} "
        f"Você também pode usar um código IATA de 3 letras maiúsculas (ex.: 'GRU')."
    )


def is_domestic(airports: list[str]) -> bool:
    if not airports:
        return False
    return all(code in BRAZIL_AIRPORTS for code in airports)
