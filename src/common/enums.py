from enum import Enum


class UserRole(str, Enum):
    TRAVELER = "TRAVELER"
    PARTNER  = "PARTNER"
    ADMIN    = "ADMIN"


class PartnerType(str, Enum):
    HOTEL   = "HOTEL"
    VEHICLE = "VEHICLE"
    GUIDE   = "GUIDE"


class PartnerStatus(str, Enum):
    APPLIED      = "APPLIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED     = "APPROVED"
    REJECTED     = "REJECTED"
    SUSPENDED    = "SUSPENDED"


class RoomType(str, Enum):
    STANDARD  = "STANDARD"
    DELUXE    = "DELUXE"
    SUITE     = "SUITE"
    FAMILY    = "FAMILY"
    DORMITORY = "DORMITORY"


class ReviewEntityType(str, Enum):
    HOTEL   = "HOTEL"
    TEMPLE  = "TEMPLE"
    GUIDE   = "GUIDE"
    PACKAGE = "PACKAGE"
    VEHICLE = "VEHICLE"