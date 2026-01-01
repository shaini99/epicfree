"""Steam Store API를 통한 평점 조회 어댑터

Steam Store API는 API 키 없이 게임 정보와 평점을 조회할 수 있습니다.
- 검색 API: 게임 제목으로 App ID 조회
- 상세 API: Metacritic 점수 포함
- 리뷰 API: Steam 사용자 리뷰 통계
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from src.domain.ports.rating_fetcher import RatingFetcher
from src.domain.value_objects.rating import Rating

if TYPE_CHECKING:
    from src.domain.entities.game import Game

logger = logging.getLogger(__name__)


class SteamApiAdapter(RatingFetcher):
    """Steam Store API를 통한 평점 조회 (API 키 불필요)"""

    SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
    DETAILS_URL = "https://store.steampowered.com/api/appdetails"
    REVIEWS_URL = "https://store.steampowered.com/appreviews/"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def fetch_rating(self, game: Game) -> Rating | None:
        """Game 엔티티로 Steam API를 통해 평점 정보 조회"""
        if not game.title:
            logger.debug(f"No title for game, skipping Steam rating")
            return None

        # 1. 게임 제목으로 Steam 검색 → App ID
        app_id = self._search_game(game.title)
        if not app_id:
            logger.debug(f"Steam search returned no results for '{game.title}'")
            return None

        # 2. App ID로 상세 정보 조회 → Metacritic
        metacritic_score = self._get_metacritic_score(app_id)

        # 3. 리뷰 정보 조회 → Steam 긍정률
        steam_positive = self._get_steam_positive(app_id)

        if metacritic_score is None and steam_positive is None:
            return None

        logger.debug(
            f"Steam rating for '{game.title}': "
            f"metacritic={metacritic_score}, steam={steam_positive}%"
        )

        return Rating(metacritic=metacritic_score, steam=steam_positive)

    def _search_game(self, title: str) -> int | None:
        """Steam 검색으로 App ID 조회"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self.SEARCH_URL,
                    params={"term": title, "l": "english", "cc": "KR"},
                )
                response.raise_for_status()
                data = response.json()

                items = data.get("items", [])
                if not items:
                    return None

                # 첫 번째 결과의 App ID 반환
                return items[0].get("id")

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.debug(f"Steam search failed for '{title}': {e}")
            return None

    def _get_metacritic_score(self, app_id: int) -> int | None:
        """앱 상세 정보에서 Metacritic 점수 조회"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self.DETAILS_URL,
                    params={"appids": app_id, "l": "korean"},
                )
                response.raise_for_status()
                data = response.json()

                app_data = data.get(str(app_id), {})
                if not app_data.get("success"):
                    return None

                game_data = app_data.get("data", {})
                metacritic = game_data.get("metacritic", {})

                return metacritic.get("score")

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.debug(f"Steam details failed for app_id={app_id}: {e}")
            return None

    def _get_steam_positive(self, app_id: int) -> int | None:
        """Steam 리뷰 통계에서 긍정률 조회"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.REVIEWS_URL}{app_id}",
                    params={"json": 1, "language": "all"},
                )
                response.raise_for_status()
                data = response.json()

                summary = data.get("query_summary", {})
                total = summary.get("total_reviews", 0)
                positive = summary.get("total_positive", 0)

                if total == 0:
                    return None

                return round(positive / total * 100)

        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.debug(f"Steam reviews failed for app_id={app_id}: {e}")
            return None
