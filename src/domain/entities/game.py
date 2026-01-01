from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.value_objects.free_period import FreePeriod
from src.domain.value_objects.genre import Genre
from src.domain.value_objects.rating import Rating


@dataclass(eq=False)
class Game:
    """Epic Games Store의 무료 게임을 나타내는 Entity"""

    id: str
    slug: str
    namespace: str  # sandboxId (Epic GraphQL 평점 조회용)
    title: str
    thumbnail: str
    epic_url: str
    free_period: FreePeriod
    genres: list[Genre]
    rating: Rating | None = None

    def __eq__(self, other: object) -> bool:
        """ID 기반 동등성 비교"""
        if not isinstance(other, Game):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """ID 기반 해시"""
        return hash(self.id)

    def is_currently_free(self) -> bool:
        """현재 무료로 제공 중인지 확인"""
        return self.free_period.is_active()

    def is_upcoming(self) -> bool:
        """다음 주 무료 게임인지 확인 (아직 무료 기간 시작 전)"""
        now = datetime.now(timezone.utc)
        return now < self.free_period.start
