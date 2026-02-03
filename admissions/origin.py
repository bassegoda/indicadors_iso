"""
Origin classification for Hospital Clínic Barcelona admissions.

Classifies each admission into one of five origin groups based on
health_area (ABS code) and, for patients registered generically as
'CATALUNYA', falls back to postcode-based classification.

Groups
------
LOCAL           Clínic catchment (old "Sector Sanitari Barcelona Esquerra"):
                  ABS sectors Ciutat Vella, Eixample, Gràcia.
BCN_CITY_OTHER  Barcelona city, outside Clínic catchment.
BCN_PROVINCE    Barcelona province municipalities (Hospitalet, Badalona, …).
CATALONIA       Rest of Catalonia (Girona, Lleida, Tarragona provinces).
EXTERNAL        Outside Catalonia (other Spanish regions, international, …).
UNKNOWN         NULL / missing in both health_area and postcode.

Usage
-----
    from origin import classify_origin
    df['origin'] = classify_origin(df)          # vectorised, returns Series
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# ABS health_area codes that fall inside the Clínic catchment.
# Source: abs.csv cross-referenced with g_demographics.health_area values.
#   Ciutat Vella  → 1A-1E
#   Eixample      → 2A-2K (no 2F in current ABS)
#   Gràcia        → 6A-6E
_LOCAL_HEALTH_AREAS = {
    "1A", "1B", "1C", "1D", "1E",
    "2A", "2B", "2C", "2D", "2E", "2G", "2H", "2I", "2J", "2K",
    "6A", "6B", "6C", "6D", "6E",
}

# All Barcelona-city ABS codes (all districts).
# Retired codes (8A, 8B, 8D, 8E, 9D, 9G, 9Z) are included so they are not
# misclassified as external.
_BCN_CITY_HEALTH_AREAS = _LOCAL_HEALTH_AREAS | {
    # Sants - Montjuïc
    "3A", "3B", "3C", "3D", "3E", "3G", "3H", "3I",
    # Les Corts
    "4A", "4B", "4C",
    # Sarrià - Sant Gervasi
    "5A", "5B", "5C", "5D", "5E",
    # Horta - Guinardó
    "7A", "7B", "7C", "7D", "7E", "7F", "7G",
    # Nou Barris (current + retired)
    "8A", "8B", "8C", "8D", "8E", "8F", "8G", "8H", "8I", "8J", "8K", "8L",
    # Sant Andreu (current + retired)
    "9A", "9C", "9D", "9E", "9F", "9G", "9H", "9I", "9Z",
    # Sant Martí
    "10A", "10B", "10C", "10D", "10E", "10F", "10G", "10H", "10I", "10J",
}

# Spanish region names as they appear in health_area (other-Spain referrals).
_SPAIN_REGIONS = {
    "BALEARES", "ARAGON", "VALENCIA", "MADRID", "GALICIA",
    "CANARIAS", "ANDALUCIA", "EUSKADI", "CASTLEON", "CASMANCHA",
    "LARIOJA", "NAVARRA", "MURCIA", "ASTURIAS", "EXTREMADU",
    "CANTABRIA", "MELILLA", "CEUTA",
}

# Country names as they appear in health_area (international referrals).
_INTERNATIONAL = {
    "ANDORRA", "FRANCESA", "ITALIA", "EE.UU.", "GRAN BRET",
    "ALEMANIA", "CHILE", "ARGENTINA", "COLOMBIA", "ARABIA SA", "SUIZA",
    "BRASIL", "PORTUGAL", "POLONIA", "HOLANDA", "BELGICA", "BÃLGICA",
    "IRLANDA", "AUSTRALIA", "CANADÃ", "CANADÁ", "RUMANÃA", "DINAMARCA",
    "HUMGRÃA", "PERÃ", "PERÚ", "UCRANIA", "COSTA RIC", "BULGARIA",
    "EGIPTO", "ECUADOR", "CHINA", "FEDERACIÓ", "FEDERACIÃ", "ESLOVENIA",
    "INDIA", "NORUEGA", "KUWAIT", "SUECIA", "MÃXICO", "VENEZUELA",
    "NUEVA ZEL", "EAU", "MALTA", "GRECIA", "MARRUECOS", "REP. DOMI",
    "ALBANIA", "GUINEA", "CROACIA", "ISLANDIA", "ARGELIA", "ISRAEL",
    "GEORGIA", "EL SALVAD", "PANAMÁ", "TAIWAN", "PUERTO RI", "SERBIA",
    "BÉLGICA", "FINLANDIA", "REP. CHEC", "JAPÃN", "SUDÃFRIC", "BIELORRUS",
}

# Postcodes that map to the Clínic catchment (Ciutat Vella + Eixample + Gràcia).
# Source: official Correos/INE assignment for Barcelona city.
_LOCAL_POSTCODES = {
    # Ciutat Vella
    "08001", "08002", "08003",
    # Eixample
    "08009", "08010", "08011", "08013", "08018", "08019", "08020",
    "08036", "08037", "08038",
    # Gràcia
    "08006", "08023", "08032",
}


# ---------------------------------------------------------------------------
# Classification helpers (scalar)
# ---------------------------------------------------------------------------

def _classify_by_health_area(ha: str | None) -> str | None:
    """
    Attempt classification from health_area alone.
    Returns the group string, or None if health_area is 'CATALUNYA'
    (needs postcode fallback) or unrecognised.
    """
    if pd.isna(ha) or ha is None or str(ha).strip() == "":
        return None                         # fall through to postcode

    ha = str(ha).strip().upper()

    if ha in _LOCAL_HEALTH_AREAS:
        return "LOCAL"
    if ha in _BCN_CITY_HEALTH_AREAS:
        return "BCN_CITY_OTHER"
    if ha == "CATALUNYA":
        return None                         # needs postcode fallback
    if ha in _SPAIN_REGIONS:
        return "EXTERNAL"
    if ha in _INTERNATIONAL:
        return "EXTERNAL"

    # Unrecognised string that is not a short ABS code and not a known region
    # — treat as external (likely a region/country with encoding variation)
    return "EXTERNAL"


def _classify_by_postcode(pc: str | None) -> str:
    """
    Fallback classification from postcode, used when health_area = 'CATALUNYA'.
    Barcelona postcodes: 080XX = city, 08100-08999 = province.
    """
    if pd.isna(pc) or pc is None or str(pc).strip() == "":
        return "UNKNOWN"

    pc = str(pc).strip()

    if not pc.isdigit():
        return "UNKNOWN"                    # e.g. 'AD100' (Andorra) edge case

    province = pc[:2]

    if province == "08":
        if pc.startswith("080"):            # 08000-08099 = Barcelona city
            return "LOCAL" if pc in _LOCAL_POSTCODES else "BCN_CITY_OTHER"
        else:                               # 08100-08999 = Barcelona province
            return "BCN_PROVINCE"
    elif province in ("17", "25", "43"):    # Girona, Lleida, Tarragona
        return "CATALONIA"
    else:
        return "EXTERNAL"


def _classify_single(health_area, postcode) -> str:
    """Full two-step classification for one row."""
    result = _classify_by_health_area(health_area)
    if result is not None:
        return result
    return _classify_by_postcode(postcode)


# ---------------------------------------------------------------------------
# Public vectorised entry-point
# ---------------------------------------------------------------------------

def classify_origin(df: pd.DataFrame,
                    ha_col: str = "health_area",
                    pc_col: str = "postcode") -> pd.Series:
    """
    Classify every row in *df* and return a Series of origin labels.

    Parameters
    ----------
    df      : DataFrame that contains at least *ha_col* and *pc_col*.
    ha_col  : column name for health_area   (default 'health_area').
    pc_col  : column name for postcode      (default 'postcode').

    Returns
    -------
    pd.Series with dtype str, same index as *df*, values in
    {LOCAL, BCN_CITY_OTHER, BCN_PROVINCE, CATALONIA, EXTERNAL, UNKNOWN}.
    """
    if ha_col not in df.columns or pc_col not in df.columns:
        raise ValueError(
            f"DataFrame must contain columns '{ha_col}' and '{pc_col}'. "
            f"Found: {list(df.columns)}"
        )

    return pd.Series(
        [_classify_single(ha, pc) for ha, pc in zip(df[ha_col], df[pc_col])],
        index=df.index,
        name="origin",
        dtype="str",
    )
