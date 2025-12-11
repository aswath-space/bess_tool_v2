
# Mapping from ISO 2-letter country codes to ENTSO-E Bidding Zones
# This is a simplified list. In reality, some countries have multiple zones (e.g., Italy, Norway, Sweden).
# For the purpose of this tool, we map to the primary/dominant zone or the one commonly used for national price reference.

ZONE_MAPPING = {
    'AT': 'AT',          # Austria
    'BE': 'BE',          # Belgium
    'BG': 'BG',          # Bulgaria
    'CH': 'CH',          # Switzerland
    'CZ': 'CZ',          # Czech Republic
    'DE': 'DE_LU',       # Germany (DE-LU is the common bidding zone)
    'DK': 'DK_1',        # Denmark (Defaulting to DK1, could be DK2)
    'EE': 'EE',          # Estonia
    'ES': 'ES',          # Spain
    'FI': 'FI',          # Finland
    'FR': 'FR',          # France
    'GR': 'GR',          # Greece
    'HR': 'HR',          # Croatia
    'HU': 'HU',          # Hungary
    'IE': 'IE_SEM',      # Ireland (SEM)
    'IT': 'IT_North',    # Italy (Defaulting to North, highly regional)
    'LT': 'LT',          # Lithuania
    'LU': 'DE_LU',       # Luxembourg (Part of DE-LU)
    'LV': 'LV',          # Latvia
    'NL': 'NL',          # Netherlands
    'NO': 'NO_1',        # Norway (Defaulting to NO1)
    'PL': 'PL',          # Poland
    'PT': 'PT',          # Portugal
    'RO': 'RO',          # Romania
    'SE': 'SE_3',        # Sweden (Defaulting to SE3 - Stockholm area)
    'SI': 'SI',          # Slovenia
    'SK': 'SK',          # Slovakia
    'UK': 'UK',          # United Kingdom (General, might need specific N2EX etc)
}

def get_entsoe_zone(country_code: str) -> str:
    """
    Returns the ENTSO-E bidding zone for a given ISO country code.
    Defaults to the country code itself if no specific mapping exists, 
    assuming the country might be its own zone.
    """
    return ZONE_MAPPING.get(country_code.upper(), country_code.upper())
