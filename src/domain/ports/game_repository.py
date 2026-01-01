from abc import ABC, abstractmethod

from src.domain.entities.game import Game


class GameRepository(ABC):
    """게임 정보를 저장하는 Port"""

    @abstractmethod
    def save(self, games: list[Game]) -> None:
        """게임 목록을 저장"""
        pass
