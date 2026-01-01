"""Epic Games 무료 게임 정보 수집 메인 스크립트"""

import sys

from src.application.use_cases.enrich_ratings import EnrichRatingsUseCase
from src.config.settings import OUTPUT_JSON_PATH
from src.domain.entities.game import Game
from src.infrastructure.adapters.composite_rating_adapter import CompositeRatingAdapter
from src.infrastructure.adapters.epic_api_adapter import EpicApiAdapter
from src.infrastructure.adapters.steam_api_adapter import SteamApiAdapter
from src.infrastructure.repositories.json_file_repo import JsonFileRepository


def create_rating_adapter() -> CompositeRatingAdapter:
    """Rating 어댑터 생성"""
    fetchers = [
        SteamApiAdapter(),  # Metacritic + Steam Reviews (API 키 불필요)
    ]
    print("✓ Steam API 활성화 (Metacritic + Steam 평점)")

    return CompositeRatingAdapter(fetchers)


def enrich_games(games: list[Game], adapter: CompositeRatingAdapter) -> list[Game]:
    """게임에 평점 정보 추가"""
    if not games:
        return games
    print("평점 정보 수집 중...")
    return EnrichRatingsUseCase(adapter).execute(games)


def main():
    """Epic Games 무료 게임 정보 수집 및 저장

    한 번의 명령으로:
    1. current/upcoming 게임 조회 및 rating 추가
    2. past 게임 중 rating 없는 게임 보강
    """
    print("Epic Games 무료 게임 정보 수집 시작...")

    # 의존성 생성
    fetcher = EpicApiAdapter()
    repository = JsonFileRepository(OUTPUT_JSON_PATH)
    rating_adapter = create_rating_adapter()

    # 1. 신규 게임 조회
    print("무료 게임 목록 조회 중...")
    games = fetcher.fetch_free_games()
    if not games:
        print("⚠️  조회된 게임이 없습니다.")
        return

    # 2. 신규 게임 rating 추가 및 저장
    games = enrich_games(games, rating_adapter)
    print("게임 정보 저장 중...")
    repository.save(games)

    # 3. past 게임 rating 보강
    past_games = repository.load_past_games_without_rating()
    past_updated = 0

    if past_games:
        print(f"\npast 게임 rating 보강 중 ({len(past_games)}개)...")
        enriched_past = enrich_games(past_games, rating_adapter)
        past_updated = repository.update_past_ratings(enriched_past)
        if past_updated > 0:
            print(f"✓ past rating {past_updated}개 보강 완료")
        else:
            print("ℹ️  보강할 past rating 없음")

    # 결과 출력
    current_count = sum(1 for g in games if g.is_currently_free())
    upcoming_count = sum(1 for g in games if g.is_upcoming())

    print("\n" + "=" * 50)
    print("✓ 작업 완료!")
    print(f"  - 현재 무료: {current_count}개")
    print(f"  - 예정: {upcoming_count}개")
    if past_updated > 0:
        print(f"  - past rating 보강: {past_updated}개")
    print(f"저장 경로: {OUTPUT_JSON_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)
