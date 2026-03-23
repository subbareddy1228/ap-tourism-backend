from enum import Enum

class BookingType(str, Enum):
    HOTEL    = "hotel"
    VEHICLE  = "vehicle"
    DARSHAN  = "darshan"
    POOJA    = "pooja"
    PRASADAM = "prasadam"
    PACKAGE  = "package"
    GUIDE    = "guide"
    COMBO    = "combo"
    CUSTOM   = "custom"

class BookingStatus(str, Enum):
    PENDING    = "pending"
    CONFIRMED  = "confirmed"
    ONGOING    = "ongoing"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"

class PaymentStatus(str, Enum):
    PENDING    = "pending"
    PAID       = "paid"
    FAILED     = "failed"
    REFUNDED   = "refunded"
    PARTIAL    = "partial"

class TripType(str, Enum):
    ONE_WAY    = "one_way"
    ROUND_TRIP = "round_trip"
    LOCAL      = "local"
    OUTSTATION = "outstation"

class Gender(str, Enum):
    MALE   = "male"
    FEMALE = "female"
    OTHER  = "other"

class DeliveryStatus(str, Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class UserRole(str, Enum):
    USER    = "user"
    GUIDE   = "guide"
    PARTNER = "partner"
    ADMIN   = "admin"
