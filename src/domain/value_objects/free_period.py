from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class FreePeriod:
    """무료 제공 기간을 나타내는 Value Object"""

    start: datetime
    end: datetime

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError(f"start must be before end: start={self.start}, end={self.end}")

    def is_active(self) -> bool:
        """현재 무료 기간이 활성화되어 있는지 확인"""
        now = datetime.now(timezone.utc)
        return self.start <= now <= self.end
