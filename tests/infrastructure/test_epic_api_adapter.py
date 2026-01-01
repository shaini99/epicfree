"""EpicApiAdapter 단위 테스트"""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from src.infrastructure.adapters.epic_api_adapter import EpicApiAdapter


class TestExtractSlug:
    """_extract_slug 메서드 테스트"""

    def test_extract_from_mappings_page_slug(self):
        """catalogNs.mappings[0].pageSlug에서 추출"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": {
                "mappings": [
                    {"pageSlug": "from-mappings"}
                ]
            },
            "productSlug": "should-not-use",
            "urlSlug": "should-not-use-either"
        }

        result = adapter._extract_slug(raw_game)
        assert result == "from-mappings"

    def test_extract_from_product_slug_when_mappings_empty(self):
        """mappings가 비어있으면 productSlug 사용"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": {
                "mappings": []
            },
            "productSlug": "from-product-slug",
            "urlSlug": "should-not-use"
        }

        result = adapter._extract_slug(raw_game)
        assert result == "from-product-slug"

    def test_extract_from_product_slug_removes_home_suffix(self):
        """productSlug의 /home 접미사 제거"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": None,
            "productSlug": "game-slug/home",
            "urlSlug": "should-not-use"
        }

        result = adapter._extract_slug(raw_game)
        assert result == "game-slug"

    def test_skip_invalid_product_slug_values(self):
        """'None', '[]' 같은 잘못된 productSlug는 건너뜀"""
        adapter = EpicApiAdapter()

        # 'None' 문자열
        raw_game = {
            "catalogNs": None,
            "productSlug": "None",
            "urlSlug": "from-url-slug"
        }
        result = adapter._extract_slug(raw_game)
        assert result == "from-url-slug"

        # '[]' 문자열
        raw_game = {
            "catalogNs": None,
            "productSlug": "[]",
            "urlSlug": "from-url-slug"
        }
        result = adapter._extract_slug(raw_game)
        assert result == "from-url-slug"

        # 빈 문자열
        raw_game = {
            "catalogNs": None,
            "productSlug": "",
            "urlSlug": "from-url-slug"
        }
        result = adapter._extract_slug(raw_game)
        assert result == "from-url-slug"

    def test_extract_from_url_slug_when_not_mysterygame(self):
        """urlSlug 사용 (mysterygame 제외)"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": None,
            "productSlug": None,
            "urlSlug": "valid-url-slug"
        }

        result = adapter._extract_slug(raw_game)
        assert result == "valid-url-slug"

    def test_skip_mysterygame_url_slug(self):
        """mysterygame으로 시작하는 urlSlug는 건너뜀"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": None,
            "productSlug": None,
            "urlSlug": "mysterygame-2025"
        }

        result = adapter._extract_slug(raw_game)
        assert result == ""

    def test_skip_uuid_format_url_slug(self):
        """UUID 형태(32자 hex)의 urlSlug는 건너뜀"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": None,
            "productSlug": None,
            "urlSlug": "a1b2c3d4e5f6789012345678901234ab"  # 32자 hex
        }

        result = adapter._extract_slug(raw_game)
        assert result == ""

    def test_return_empty_when_no_valid_slug(self):
        """유효한 slug가 없으면 빈 문자열 반환"""
        adapter = EpicApiAdapter()
        raw_game = {
            "catalogNs": None,
            "productSlug": None,
            "urlSlug": None
        }

        result = adapter._extract_slug(raw_game)
        assert result == ""


class TestExtractFreePeriod:
    """_extract_free_period 메서드 테스트"""

    def test_extract_from_promotional_offers(self):
        """promotionalOffers에서 무료 기간 추출 (discountPercentage=0)"""
        adapter = EpicApiAdapter()
        promotions = {
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

        result = adapter._extract_free_period(promotions)

        assert result is not None
        assert result.start == datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result.end == datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)

    def test_extract_from_upcoming_offers(self):
        """upcomingPromotionalOffers에서 무료 기간 추출 (discountPercentage=0)"""
        adapter = EpicApiAdapter()
        promotions = {
            "promotionalOffers": [],
            "upcomingPromotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": "2025-02-01T00:00:00.000Z",
                            "endDate": "2025-02-08T00:00:00.000Z",
                            "discountSetting": {
                                "discountType": "PERCENTAGE",
                                "discountPercentage": 0
                            }
                        }
                    ]
                }
            ]
        }

        result = adapter._extract_free_period(promotions)

        assert result is not None
        assert result.start == datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result.end == datetime(2025, 2, 8, 0, 0, 0, tzinfo=timezone.utc)

    def test_return_none_when_no_offers(self):
        """오퍼가 없으면 None 반환"""
        adapter = EpicApiAdapter()
        promotions = {
            "promotionalOffers": [],
            "upcomingPromotionalOffers": []
        }

        result = adapter._extract_free_period(promotions)
        assert result is None

    def test_return_none_when_dates_missing(self):
        """날짜 정보가 없으면 None 반환"""
        adapter = EpicApiAdapter()
        promotions = {
            "promotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": None,
                            "endDate": None
                        }
                    ]
                }
            ],
            "upcomingPromotionalOffers": []
        }

        result = adapter._extract_free_period(promotions)
        assert result is None

    @patch('src.infrastructure.adapters.epic_api_adapter.logger')
    def test_handle_invalid_date_format(self, mock_logger):
        """잘못된 날짜 형식은 경고 로그 후 건너뜀"""
        adapter = EpicApiAdapter()
        promotions = {
            "promotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": "invalid-date",
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

        result = adapter._extract_free_period(promotions)

        assert result is None
        assert mock_logger.warning.called

    def test_handle_z_timezone_format(self):
        """'Z' 형식의 타임존을 UTC로 변환"""
        adapter = EpicApiAdapter()
        promotions = {
            "promotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": "2025-01-01T12:30:00Z",
                            "endDate": "2025-01-08T23:59:59Z",
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

        result = adapter._extract_free_period(promotions)

        assert result is not None
        assert result.start.tzinfo == timezone.utc
        assert result.end.tzinfo == timezone.utc

    def test_skip_non_free_offers(self):
        """discountPercentage가 0이 아닌 할인 오퍼는 무시"""
        adapter = EpicApiAdapter()
        promotions = {
            "promotionalOffers": [
                {
                    "promotionalOffers": [
                        {
                            "startDate": "2025-01-01T00:00:00.000Z",
                            "endDate": "2025-01-08T00:00:00.000Z",
                            "discountSetting": {
                                "discountType": "PERCENTAGE",
                                "discountPercentage": 20  # 80% 할인 = 무료 아님
                            }
                        }
                    ]
                }
            ],
            "upcomingPromotionalOffers": []
        }

        result = adapter._extract_free_period(promotions)
        assert result is None  # 무료가 아니므로 None


class TestConvertToGameEntity:
    """_convert_to_game_entity 메서드 테스트"""

    def test_convert_base_game_to_entity(self, sample_raw_game_data: dict[str, Any]):
        """일반 게임을 Game 엔티티로 변환"""
        adapter = EpicApiAdapter()

        result = adapter._convert_to_game_entity(sample_raw_game_data)

        assert result is not None
        assert result.id == "test-game-id"
        assert result.slug == "test-game-slug"
        assert result.title == "Test Game"
        assert result.epic_url == "https://store.epicgames.com/ko/p/test-game-slug"
        assert result.thumbnail == "https://example.com/thumbnail.jpg"
        assert len(result.genres) == 2
        assert result.genres[0].name == "Action"
        assert result.genres[1].name == "Adventure"

    def test_convert_bundle_game_uses_bundles_path(self, sample_bundle_raw_game_data: dict[str, Any]):
        """BUNDLE 타입 게임은 /bundles/ 경로 사용"""
        adapter = EpicApiAdapter()

        result = adapter._convert_to_game_entity(sample_bundle_raw_game_data)

        assert result is not None
        assert result.epic_url == "https://store.epicgames.com/ko/bundles/test-bundle-slug"

    def test_bundle_category_uses_bundles_path(self, sample_raw_game_data: dict[str, Any]):
        """bundles 카테고리가 있으면 /bundles/ 경로 사용"""
        adapter = EpicApiAdapter()
        raw_game = {
            **sample_raw_game_data,
            "offerType": "OTHERS",
            "categories": [
                {"path": "freegames"},
                {"path": "bundles"},
            ],
        }

        result = adapter._convert_to_game_entity(raw_game)

        assert result is not None
        assert result.epic_url == "https://store.epicgames.com/ko/bundles/test-game-slug"

    def test_return_none_when_no_promotions(self):
        """프로모션이 없으면 None 반환"""
        adapter = EpicApiAdapter()
        raw_game = {
            "id": "test-id",
            "title": "Test Game",
            "promotions": None
        }

        result = adapter._convert_to_game_entity(raw_game)
        assert result is None

    def test_return_none_when_no_free_period(self):
        """무료 기간이 없으면 None 반환"""
        adapter = EpicApiAdapter()
        raw_game = {
            "id": "test-id",
            "title": "Test Game",
            "promotions": {
                "promotionalOffers": [],
                "upcomingPromotionalOffers": []
            }
        }

        result = adapter._convert_to_game_entity(raw_game)
        assert result is None

    @patch('src.infrastructure.adapters.epic_api_adapter.logger')
    def test_return_none_when_id_empty(self, mock_logger):
        """게임 ID가 비어있으면 경고 로그 후 None 반환"""
        adapter = EpicApiAdapter()
        raw_game = {
            "id": "",
            "title": "Test Game",
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

        result = adapter._convert_to_game_entity(raw_game)

        assert result is None
        assert mock_logger.warning.called

    def test_epic_url_empty_when_no_slug(self):
        """slug가 없으면 epic_url은 빈 문자열"""
        adapter = EpicApiAdapter()
        raw_game = {
            "id": "test-id",
            "title": "Test Game",
            "catalogNs": None,
            "productSlug": None,
            "urlSlug": None,
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

        result = adapter._convert_to_game_entity(raw_game)

        assert result is not None
        assert result.slug == ""
        assert result.epic_url == ""


class TestFetchFreeGames:
    """fetch_free_games 메서드 테스트"""

    @patch.object(EpicApiAdapter, '_convert_to_game_entity')
    def test_fetch_free_games_success(self, mock_convert, sample_game):
        """무료 게임 조회 성공"""
        adapter = EpicApiAdapter()

        # Mock API 응답
        adapter.api.get_free_games = MagicMock(return_value={
            "data": {
                "Catalog": {
                    "searchStore": {
                        "elements": [
                            {"id": "game-1"},
                            {"id": "game-2"}
                        ]
                    }
                }
            }
        })

        # Mock 변환 결과
        mock_convert.return_value = sample_game

        result = adapter.fetch_free_games()

        assert len(result) == 2
        assert mock_convert.call_count == 2

    @patch.object(EpicApiAdapter, '_convert_to_game_entity')
    def test_fetch_free_games_filters_none_results(self, mock_convert):
        """None을 반환하는 게임은 필터링"""
        adapter = EpicApiAdapter()

        adapter.api.get_free_games = MagicMock(return_value={
            "data": {
                "Catalog": {
                    "searchStore": {
                        "elements": [
                            {"id": "game-1"},
                            {"id": "game-2"}
                        ]
                    }
                }
            }
        })

        # 첫 번째는 None, 두 번째는 유효한 게임
        mock_convert.side_effect = [None, MagicMock()]

        result = adapter.fetch_free_games()

        assert len(result) == 1

    @patch('src.infrastructure.adapters.epic_api_adapter.logger')
    def test_fetch_free_games_handles_api_error(self, mock_logger):
        """API 에러 발생 시 빈 리스트 반환"""
        adapter = EpicApiAdapter()
        adapter.api.get_free_games = MagicMock(side_effect=Exception("API Error"))

        result = adapter.fetch_free_games()

        assert result == []
        assert mock_logger.error.called
