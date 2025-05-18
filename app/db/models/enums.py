# app/db/models/enums.py

from enum import Enum

class UserType(str, Enum):
    CHILD = "child"
    PARENT = "parent"
    ADMIN = "admin"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class AsdLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NO_ASD = "noAsd"

class DayOfWeek(str, Enum):
    MON = "Mon"
    TUE = "Tue"
    WED = "Wed"
    THU = "Thu"
    FRI = "Fri"
    SAT = "Sat"
    SUN = "Sun"

class GridLayoutTypeEnum(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    DENSE = "dense"

class TextSizeTypeEnum(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class ContrastModeTypeEnum(str, Enum):
    DEFAULT = "default"
    HIGH_CONTRAST_LIGHT = "high-contrast-light"
    HIGH_CONTRAST_DARK = "high-contrast-dark"