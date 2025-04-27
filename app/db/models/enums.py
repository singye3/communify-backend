# app/db/models/enums.py
from enum import Enum

# --- User Enums ---
class UserType(str, Enum):
    CHILD = "child"
    PARENT = "parent"
    ADMIN = "admin" # Example

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending" # Example

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

# --- Settings Enums (from schemas/settings.py - can keep central) ---
# You might already have these defined in schemas/settings.py
# If so, you can import them instead of redefining. For clarity, I'll redefine here.
class AsdLevel(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    NO_ASD = 'noAsd'

class DayOfWeek(str, Enum):
    MON = 'Mon'
    TUE = 'Tue'
    WED = 'Wed'
    THU = 'Thu'
    FRI = 'Fri'
    SAT = 'Sat'
    SUN = 'Sun'

# --- Appearance Enums (if defined in frontend/context) ---
class GridLayoutTypeEnum(str, Enum): # Rename to avoid conflict with type alias
    SIMPLE = 'simple'
    STANDARD = 'standard'
    DENSE = 'dense'

class TextSizeTypeEnum(str, Enum): # Rename to avoid conflict with type alias
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'

class ContrastModeTypeEnum(str, Enum): # Rename to avoid conflict with type alias
    DEFAULT = 'default'
    HIGH_CONTRAST_LIGHT = 'high-contrast-light'
    HIGH_CONTRAST_DARK = 'high-contrast-dark'