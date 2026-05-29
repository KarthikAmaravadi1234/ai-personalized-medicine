from enum import Enum


class Sex(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"
