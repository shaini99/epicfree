"""여러 평점 소스를 결합하는 Composite 어댑터"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.ports.rating_fetcher import RatingFetcher
from src.domain.value_objects.rating import Rating

if TYPE_CHECKING:
    from src.domain.entities.game import Game

logger = logging.getLogger(__name__)


class CompositeRatingAdapter(RatingFetcher):
    """여러 RatingFetcher 결과를 병합하는 Composite Adapter

    결합 순서:
    1. EpicRatingAdapter → opencritic(0-100) (현재 동작 안함)
    2. SteamApiAdapter → metacritic(0-100), steam(0-100)

    결과: Rating(metacritic, opencritic, steam)
    """

    def __init__(self, fetchers: list[RatingFetcher]):
        self.fetchers = fetchers

    def fetch_rating(self, game: Game) -> Rating | None:
        """모든 fetcher에서 평점을 조회하고 결과를 병합"""
        epic_score: float | None = None
        metacritic_score: int | None = None
        opencritic_score: int | None = None
        steam_score: int | None = None

        for fetcher in self.fetchers:
            try:
                rating = fetcher.fetch_rating(game)
                if rating:
                    # 각 소스의 점수를 병합 (먼저 찾은 값 우선)
                    if epic_score is None and rating.epic is not None:
                        epic_score = rating.epic
                    if metacritic_score is None and rating.metacritic is not None:
                        metacritic_score = rating.metacritic
                    if opencritic_score is None and rating.opencritic is not None:
                        opencritic_score = rating.opencritic
                    if steam_score is None and rating.steam is not None:
                        steam_score = rating.steam
            except Exception as e:
                fetcher_name = fetcher.__class__.__name__
                logger.warning(f"{fetcher_name} failed for '{game.title}': {e}")
                continue

        if epic_score is None and metacritic_score is None and opencritic_score is None and steam_score is None:
            return None

        return Rating(
            epic=epic_score,
            metacritic=metacritic_score,
            opencritic=opencritic_score,
            steam=steam_score,
        )
