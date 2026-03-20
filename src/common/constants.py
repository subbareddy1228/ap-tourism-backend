

# ─────────────────────────────────────────────
# AP Tourism Backend — Constants
# ─────────────────────────────────────────────

# Redis TTLs (in seconds)
CACHE_TTL_FEATURED       = 3600    # 1 hour  — featured temples/packages
CACHE_TTL_POPULAR        = 1800    # 30 min  — popular temples
CACHE_TTL_DARSHAN_SLOTS  = 120     # 2 min   — slot availability (changes fast)
CACHE_TTL_TEMPLE_DETAIL  = 900     # 15 min  — temple detail page

# Slot lock TTL (in seconds)
SLOT_LOCK_TTL            = 900     # 15 min  — hold slot while user pays

# Pagination defaults
DEFAULT_PAGE_SIZE         = 20
MAX_PAGE_SIZE             = 100

# Nearby search default radius
DEFAULT_NEARBY_RADIUS_KM  = 50.0

# Darshan slot lookahead (days)
DARSHAN_SLOT_LOOKAHEAD_DAYS = 30

# Booking reference prefixes
REF_PREFIX_DARSHAN    = "DRS"
REF_PREFIX_POOJA      = "POJ"
REF_PREFIX_PRASADAM   = "PRS"

# AP Districts (for validation/dropdown)
AP_DISTRICTS = [
    "Alluri Sitharama Raju",
    "Anakapalli",
    "Ananthapuramu",
    "Annamayya",
    "Bapatla",
    "Chittoor",
    "Dr. B.R. Ambedkar Konaseema",
    "East Godavari",
    "Eluru",
    "Guntur",
    "Kakinada",
    "Krishna",
    "Kurnool",
    "Nandyal",
    "NTR",
    "Palnadu",
    "Parvathipuram Manyam",
    "Prakasam",
    "Sri Potti Sriramulu Nellore",
    "Sri Sathya Sai",
    "Srikakulam",
    "Tirupati",
    "Visakhapatnam",
    "Vizianagaram",
    "West Godavari",
    "YSR Kadapa",
]