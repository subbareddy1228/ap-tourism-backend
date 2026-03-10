from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    TRAVELER = "traveler"
    PARTNER = "partner"
    GUIDE = "guide"
    DRIVER = "driver"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"