import enum

class UserRole(str, enum.Enum):
    TRAVELER = "traveler"
    GUIDE    = "guide"
    DRIVER   = "driver"
    PARTNER  = "partner"
    ADMIN    = "admin"


class KYCStatus(str, enum.Enum):
    PENDING  = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Gender(str, enum.Enum):
    MALE   = "male"
    FEMALE = "female"
    OTHER  = "other"


class OTPPurpose(str, enum.Enum):
    # ERD: otp_logs.purpose = login|register|reset
    LOGIN    = "login"
    REGISTER = "register"
    RESET    = "reset"
