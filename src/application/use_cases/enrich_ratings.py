from dataclasses import replace

from src.domain.entities.game import Game
from src.domain.ports.rating_fetcher import RatingFetcher


class EnrichRatingsUseCase:
    """게임 목록에 평점 정보를 추가하는 Use Case"""

    def __init__(self, rating_fetcher: RatingFetcher):
        self.rating_fetcher = rating_fetcher

    def execute(self, games: list[Game]) -> list[Game]:
        """각 게임에 대해 평점 정보를 조회하여 추가"""
        enriched_games = []

        for game in games:
            rating = self.rating_fetcher.fetch_rating(game)
            enriched_game = replace(game, rating=rating)
            enriched_games.append(enriched_game)

        return enriched_games
