from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.domain.value_objects.rating import Rating

if TYPE_CHECKING:
    from src.domain.entities.game import Game


class RatingFetcher(ABC):
    """게임 평점 정보를 가져오는 Port"""

    @abstractmethod
    def fetch_rating(self, game: "Game") -> Rating | None:
        """Game 엔티티로 평점 정보 조회 (namespace, slug 접근 필요)"""
        pass
