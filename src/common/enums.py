from enum import Enum


# ─────────────────────────────────────────────
# Darshan Type Enums
# Used by: Temple module, Booking module
# ─────────────────────────────────────────────
class DarshanType(str, Enum):
    FREE = "FREE"
    SPECIAL_ENTRY = "SPECIAL_ENTRY"
    SUPRABHATA = "SUPRABHATA"
    VIP = "VIP"


# ─────────────────────────────────────────────
# Booking Status Enums
# Used by: Temple module, Booking module, Payment module
# ─────────────────────────────────────────────
class BookingStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"


# ─────────────────────────────────────────────
# Payment Status Enums
# Used by: Payment module
# ─────────────────────────────────────────────
class PaymentStatus(str, Enum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# ─────────────────────────────────────────────
# Order Status Enums
# Used by: Temple module — prasadam orders
# ─────────────────────────────────────────────
class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    READY = "READY"
    PICKED_UP = "PICKED_UP"
    CANCELLED = "CANCELLED"


# ─────────────────────────────────────────────
# ID Proof Types
# Used by: Temple module — pilgrim details
# ─────────────────────────────────────────────
class IdProofType(str, Enum):
    AADHAR = "AADHAR"
    PAN = "PAN"
    PASSPORT = "PASSPORT"
    VOTER_ID = "VOTER_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"