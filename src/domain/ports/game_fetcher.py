from abc import ABC, abstractmethod

from src.domain.entities.game import Game


class GameFetcher(ABC):
    """Epic Games Store에서 무료 게임 정보를 가져오는 Port"""

    @abstractmethod
    def fetch_free_games(self) -> list[Game]:
        """현재 및 다음 주 무료 게임 목록 조회"""
        pass
