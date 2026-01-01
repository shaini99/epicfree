"""pytest 공통 픽스처 정의"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.domain.entities.game import Game
from src.domain.value_objects.free_period import FreePeriod
from src.domain.value_objects.genre import Genre
from src.domain.value_objects.rating import Rating


@pytest.fixture
def sample_free_period() -> FreePeriod:
    """샘플 무료 기간 픽스처"""
    return FreePeriod(
        start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_genres() -> list[Genre]:
    """샘플 장르 목록 픽스처"""
    return [
        Genre(id=0, name="Action"),
        Genre(id=1, name="Adventure"),
    ]


@pytest.fixture
def sample_rating() -> Rating:
    """샘플 평점 픽스처"""
    return Rating(epic=4.5, metacritic=85, opencritic=88)


@pytest.fixture
def sample_game(sample_free_period: FreePeriod, sample_genres: list[Genre]) -> Game:
    """샘플 게임 엔티티 픽스처"""
    return Game(
        id="test-game-id",
        slug="test-game-slug",
        namespace="test-namespace",
        title="Test Game",
        thumbnail="https://example.com/thumbnail.jpg",
        epic_url="https://store.epicgames.com/ko/p/test-game-slug",
        free_period=sample_free_period,
        genres=sample_genres,
    )


@pytest.fixture
def sample_game_with_rating(
    sample_game: Game,
    sample_rating: Rating,
) -> Game:
    """평점이 있는 샘플 게임 엔티티 픽스처"""
    sample_game.rating = sample_rating
    return sample_game


@pytest.fixture
def sample_raw_game_data() -> dict[str, Any]:
    """Epic API에서 반환되는 원시 게임 데이터 픽스처"""
    return {
        "id": "test-game-id",
        "namespace": "test-namespace",
        "title": "Test Game",
        "offerType": "BASE_GAME",
        "urlSlug": "test-game-slug",
        "productSlug": "test-game-slug",
        "catalogNs": {
            "mappings": [
                {"pageSlug": "test-game-slug"}
            ]
        },
        "keyImages": [
            {
                "type": "OfferImageWide",
                "url": "https://example.com/thumbnail.jpg"
            }
        ],
        "categories": [
            {"path": "genre/action"},
            {"path": "genre/adventure"}
        ],
        "promotions": {
            "promotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": "2025-01-01T00:00:00.000Z",
                            "endDate": "2025-01-08T00:00:00.000Z",
                            "discountSetting": {
                                "discountType": "PERCENTAGE",
                                "discountPercentage": 0  # 0 = 100% 할인 = 무료
                            }
                        }
                    ]
                }
            ],
            "upcomingPromotionalOffers": []
        }
    }


@pytest.fixture
def sample_bundle_raw_game_data() -> dict[str, Any]:
    """BUNDLE 타입 원시 게임 데이터 픽스처"""
    return {
        "id": "bundle-game-id",
        "namespace": "bundle-namespace",
        "title": "Test Bundle",
        "offerType": "BUNDLE",
        "urlSlug": "test-bundle-slug",
        "productSlug": "test-bundle-slug",
        "catalogNs": {
            "mappings": [
                {"pageSlug": "test-bundle-slug"}
            ]
        },
        "keyImages": [
            {
                "type": "OfferImageWide",
                "url": "https://example.com/bundle.jpg"
            }
        ],
        "categories": [],
        "promotions": {
            "promotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": "2025-01-01T00:00:00.000Z",
                            "endDate": "2025-01-08T00:00:00.000Z",
                            "discountSetting": {
                                "discountType": "PERCENTAGE",
                                "discountPercentage": 0
                            }
                        }
                    ]
                }
            ],
            "upcomingPromotionalOffers": []
        }
    }


@pytest.fixture
def temp_json_file(tmp_path: Path) -> Path:
    """임시 JSON 파일 경로 픽스처"""
    return tmp_path / "games.json"


@pytest.fixture
def sample_json_data() -> dict[str, Any]:
    """샘플 JSON 데이터 픽스처"""
    return {
        "updated": "2025-01-01T00:00:00+00:00",
        "currentFree": [
            {
                "id": "current-game-1",
                "slug": "current-game-slug",
                "namespace": "current-namespace",
                "title": "Current Game 1",
                "thumbnail": "https://example.com/current.jpg",
                "epicUrl": "https://store.epicgames.com/ko/p/current-game-slug",
                "freePeriod": {
                    "start": "2025-01-01T00:00:00+00:00",
                    "end": "2025-01-08T00:00:00+00:00"
                },
                "genres": [
                    {"id": 0, "name": "Action"}
                ]
            }
        ],
        "upcoming": [],
        "past": [
            {
                "id": "past-game-1",
                "slug": "past-game-slug",
                "namespace": "past-namespace",
                "title": "Past Game 1",
                "thumbnail": "https://example.com/past.jpg",
                "epicUrl": "https://store.epicgames.com/ko/p/past-game-slug",
                "freePeriod": {
                    "start": "2024-12-01T00:00:00+00:00",
                    "end": "2024-12-08T00:00:00+00:00"
                },
                "genres": [
                    {"id": 0, "name": "RPG"}
                ]
            }
        ]
    }
