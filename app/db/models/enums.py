# app/db/models/enums.py
from enum import Enum


class UserType(str, Enum):
    """Defines the possible roles or types for a user account."""

    CHILD = "child"
    PARENT = "parent"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """Defines the possible statuses for a user account."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Gender(str, Enum):
    """Defines options for user gender identity (optional field)."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AsdLevel(str, Enum):
    """Defines optional ASD support levels for tailoring aids."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NO_ASD = "noAsd"


class DayOfWeek(str, Enum):
    """Represents the days of the week, used for scheduling (e.g., downtime)."""

    MON = "Mon"
    TUE = "Tue"
    WED = "Wed"
    THU = "Thu"
    FRI = "Fri"
    SAT = "Sat"
    SUN = "Sun"


class GridLayoutTypeEnum(str, Enum):
    """Defines the available density options for the symbol grid layout."""

    SIMPLE = "simple"
    STANDARD = "standard"
    DENSE = "dense"


class TextSizeTypeEnum(str, Enum):
    """Defines the available base text size options for the application UI."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ContrastModeTypeEnum(str, Enum):
    """Defines the available color contrast themes."""

    DEFAULT = "default"
    HIGH_CONTRAST_LIGHT = "high-contrast-light"
    HIGH_CONTRAST_DARK = "high-contrast-dark"
