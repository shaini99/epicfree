import logging
from datetime import datetime

from epicstore_api import EpicGamesStoreAPI

from src.domain.entities.game import Game
from src.domain.ports.game_fetcher import GameFetcher
from src.domain.value_objects.free_period import FreePeriod
from src.domain.value_objects.genre import Genre

logger = logging.getLogger(__name__)


class EpicApiAdapter(GameFetcher):
    """epicstore_api 라이브러리를 사용한 GameFetcher 구현"""

    def __init__(self):
        self.api = EpicGamesStoreAPI()

    def fetch_free_games(self) -> list[Game]:
        """Epic Games Store에서 현재 및 예정 무료 게임 조회"""
        try:
            raw_games = self.api.get_free_games()
        except Exception as e:
            logger.error(f"Failed to fetch free games from Epic API: {e}")
            return []

        games = []

        for raw_game in raw_games.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", []):
            game = self._convert_to_game_entity(raw_game)
            if game:
                games.append(game)

        return games

    def _convert_to_game_entity(self, raw_game: dict) -> Game | None:
        """API 응답을 Game 엔티티로 변환"""
        promotions = raw_game.get("promotions")
        if not promotions:
            return None

        free_period = self._extract_free_period(promotions)
        if not free_period:
            return None

        # 필수 필드 검증
        game_id = raw_game.get("id", "")
        if not game_id or not game_id.strip():
            logger.warning(f"Game with empty id detected, title: {raw_game.get('title', 'Unknown')}")
            return None

        slug = self._extract_slug(raw_game)
        offer_type = raw_game.get("offerType", "")
        categories = raw_game.get("categories", []) or []
        is_bundle_category = any(category.get("path") == "bundles" for category in categories)
        # BUNDLE 타입 또는 bundles 카테고리는 /bundles/ 경로
        url_path = "bundles" if offer_type == "BUNDLE" or is_bundle_category else "p"
        epic_url = f"https://store.epicgames.com/ko/{url_path}/{slug}" if slug else ""

        # namespace (sandboxId) 추출 - Epic GraphQL 평점 조회에 필요
        namespace = raw_game.get("namespace", "")

        return Game(
            id=game_id,
            slug=slug,
            namespace=namespace,
            title=raw_game.get("title", ""),
            thumbnail=self._extract_thumbnail(raw_game),
            epic_url=epic_url,
            free_period=free_period,
            genres=self._extract_genres(raw_game),
        )

    def _extract_slug(self, raw_game: dict) -> str:
        """게임 slug 추출 (여러 소스에서 우선순위로 시도)"""
        # 1. catalogNs.mappings에서 pageSlug
        catalog_ns = raw_game.get("catalogNs")
        if catalog_ns:
            mappings = catalog_ns.get("mappings") or []
            if mappings and len(mappings) > 0:
                page_slug = mappings[0].get("pageSlug", "")
                if page_slug:
                    return page_slug

        # 2. productSlug (None, [], 빈 문자열 제외)
        product_slug = raw_game.get("productSlug", "")
        if product_slug and product_slug not in ("None", "[]", ""):
            # /home 접미사 제거
            if product_slug.endswith("/home"):
                product_slug = product_slug[:-5]
            return product_slug

        # 3. urlSlug (UUID 형태 및 mysterygame 제외)
        url_slug = raw_game.get("urlSlug", "")
        if url_slug and not url_slug.startswith("mysterygame"):
            # UUID 형태 체크 (32자 hex)
            if not (len(url_slug) == 32 and url_slug.isalnum()):
                return url_slug

        return ""

    def _extract_free_period(self, promotions: dict) -> FreePeriod | None:
        """프로모션 정보에서 무료 기간 추출

        핵심: discountPercentage == 0 인 경우에만 무료!
        - 0 = 100% 할인 = 완전 무료
        - 20 = 80% 할인 = 유료 (무료 아님)
        """
        promotional_offers = promotions.get("promotionalOffers", [])
        upcoming_offers = promotions.get("upcomingPromotionalOffers", [])

        all_offers = promotional_offers + upcoming_offers

        for offer_group in all_offers:
            offers = offer_group.get("promotionalOffers", [])
            for offer in offers:
                # 핵심 검증: discountPercentage가 0인 경우에만 무료
                discount_setting = offer.get("discountSetting", {})
                discount_percentage = discount_setting.get("discountPercentage")

                # discountPercentage가 0이 아니면 무료가 아님 (할인 게임)
                if discount_percentage != 0:
                    continue

                start_date = offer.get("startDate")
                end_date = offer.get("endDate")

                if start_date and end_date:
                    try:
                        return FreePeriod(
                            start=datetime.fromisoformat(start_date.replace("Z", "+00:00")),
                            end=datetime.fromisoformat(end_date.replace("Z", "+00:00")),
                        )
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"Failed to parse free period dates (start: {start_date}, end: {end_date}): {e}")
                        continue

        return None

    def _extract_thumbnail(self, raw_game: dict) -> str:
        """게임 썸네일 이미지 URL 추출"""
        images = raw_game.get("keyImages", [])
        for image in images:
            if image.get("type") == "OfferImageWide":
                return image.get("url", "")

        if images:
            return images[0].get("url", "")

        return ""

    def _extract_genres(self, raw_game: dict) -> list[Genre]:
        """게임 장르 정보 추출 (categories → tags 순으로 시도)"""
        genres = []
        seen_names: set[str] = set()  # 중복 방지
        idx = 0

        # 1차: categories 필드에서 장르 추출
        categories = raw_game.get("categories", [])
        for category in categories:
            path = category.get("path", "")
            if path.startswith("genre/"):
                genre_name = path.replace("genre/", "").replace("-", " ").title()
                if genre_name and genre_name not in seen_names:
                    genres.append(Genre(id=idx, name=genre_name))
                    seen_names.add(genre_name)
                    idx += 1

        # 2차: tags 필드에서 장르 추출 (categories에서 못 찾은 경우)
        if not genres:
            tags = raw_game.get("tags", [])
            for tag in tags:
                # tags는 {"id": "...", "name": "..."} 형태
                tag_name = tag.get("name", "")
                # 일반적인 장르 키워드 필터링
                genre_keywords = {
                    "action", "adventure", "rpg", "puzzle", "strategy",
                    "simulation", "sports", "racing", "shooter", "platformer",
                    "horror", "survival", "indie", "casual", "arcade",
                    "fighting", "roguelike", "open world", "sandbox"
                }
                tag_lower = tag_name.lower()
                if tag_lower in genre_keywords and tag_name not in seen_names:
                    genres.append(Genre(id=idx, name=tag_name.title()))
                    seen_names.add(tag_name)
                    idx += 1

        return genres
