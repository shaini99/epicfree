from dataclasses import dataclass


@dataclass(frozen=True)
class Genre:
    """게임 장르를 나타내는 Value Object"""

    id: int
    name: str
