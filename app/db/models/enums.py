# app/db/models/enums.py
from enum import Enum

# =====================================
# User Related Enumerations
# =====================================

class UserType(str, Enum):
    """Defines the possible roles or types for a user account."""
    CHILD = "child"         # Represents a child user profile
    PARENT = "parent"       # Represents a parent/guardian/caregiver user
    ADMIN = "admin"         # Represents an administrator with elevated privileges

class UserStatus(str, Enum):
    """Defines the possible statuses for a user account."""
    ACTIVE = "active"       # User account is active and can be used
    INACTIVE = "inactive"     # User account is deactivated (e.g., manually by admin)
    PENDING = "pending"     # User account requires verification or approval (optional)
    # SUSPENDED = "suspended" # Example: Temporarily disabled user

class Gender(str, Enum):
    """Defines options for user gender identity (optional field)."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"           

# =====================================
# Parental Settings Enumerations
# =====================================

class AsdLevel(str, Enum):
    """Defines optional ASD support levels for tailoring aids."""
    LOW = 'low'             # Corresponds to Level 1 support needs
    MEDIUM = 'medium'       # Corresponds to Level 2 support needs
    HIGH = 'high'           # Corresponds to Level 3 support needs
    NO_ASD = 'noAsd'        # Indicates no specific ASD-related tailoring is selected

class DayOfWeek(str, Enum):
    """Represents the days of the week, used for scheduling (e.g., downtime)."""
    MON = 'Mon'
    TUE = 'Tue'
    WED = 'Wed'
    THU = 'Thu'
    FRI = 'Fri'
    SAT = 'Sat'
    SUN = 'Sun'

# =====================================
# Appearance Settings Enumerations
# =====================================

class GridLayoutTypeEnum(str, Enum):
    """Defines the available density options for the symbol grid layout."""
    SIMPLE = 'simple'       # Fewer, larger symbols
    STANDARD = 'standard'     # Balanced number of symbols (default)
    DENSE = 'dense'         # More, smaller symbols

class TextSizeTypeEnum(str, Enum):
    """Defines the available base text size options for the application UI."""
    SMALL = 'small'
    MEDIUM = 'medium'       # Default text size
    LARGE = 'large'

class ContrastModeTypeEnum(str, Enum):
    """Defines the available color contrast themes."""
    DEFAULT = 'default'                     # Standard light or dark theme (based on dark_mode_enabled)
    HIGH_CONTRAST_LIGHT = 'high-contrast-light' # High contrast theme with a light background
    HIGH_CONTRAST_DARK = 'high-contrast-dark'  # High contrast theme with a dark background

# =====================================
# (Optional) Symbol Related Enumerations
# =====================================
# Keep these if you decide to manage standard/custom symbols on the backend later

# class AccessibilityStatus(str, Enum):
#     """Defines the accessibility review status for a symbol."""
#     ACCESSIBLE = "accessible"
#     NEEDS_REVIEW = "needs_review"
#     INACCESSIBLE = "inaccessible"

# class SharingStatus(str, Enum):
#     """Defines the sharing status for custom symbols."""
#     PRIVATE = "private"
#     PUBLIC = "public"
#     SHARED = "shared" # Example: Shared with specific users/groups