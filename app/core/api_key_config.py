from dataclasses import dataclass
from enum import Enum
from typing import Optional


class KeyType(Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    PERMANENT = "permanent"


@dataclass
class APIKey:
    key: str
    provider: str
    key_type: KeyType
    service: str
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    used_today: int = 0
    used_this_month: int = 0
    is_exhausted: bool = False
    last_reset_date: str = ""
    last_reset_month: str = ""
