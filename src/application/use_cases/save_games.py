from datetime import datetime, timezone
from typing import Callable

from src.domain.entities.game import Game


class SaveGamesUseCase:
    """게임 목록을 저장 가능한 스냅샷으로 변환"""

    def __init__(self, game_to_dict: Callable[[Game], dict]):
        self._game_to_dict = game_to_dict

    def execute(self, games: list[Game], existing_data: dict) -> dict:
        existing_past = {g["id"]: g for g in existing_data.get("past", [])}
        existing_current = {g["id"]: g for g in existing_data.get("currentFree", [])}

        current_free, upcoming = self._categorize_games(games)

        current_ids = {g["id"] for g in current_free}
        upcoming_ids = {g["id"] for g in upcoming}

        # 과거 무료였던 게임이 다시 무료가 되면 past에서 제거
        for game_id in current_ids | upcoming_ids:
            existing_past.pop(game_id, None)

        # currentFree에 있던 게임이 더 이상 보이지 않으면 past로 이동
        for game_id, game_dict in existing_current.items():
            if game_id not in current_ids and game_id not in upcoming_ids:
                existing_past[game_id] = game_dict

        past_list = sorted(existing_past.values(), key=self._past_sort_key, reverse=True)

        return {
            "updated": datetime.now(timezone.utc).isoformat(),
            "currentFree": current_free,
            "upcoming": upcoming,
            "past": past_list,
        }

    def _categorize_games(self, games: list[Game]) -> tuple[list[dict], list[dict]]:
        """게임 목록을 현재 무료와 예정으로 분류 (중복 제거)"""
        current_free_dict = {}
        upcoming_dict = {}

        for game in games:
            game_dict = self._game_to_dict(game)
            if game.is_currently_free():
                current_free_dict[game.id] = game_dict
            elif game.is_upcoming():
                upcoming_dict[game.id] = game_dict

        return list(current_free_dict.values()), list(upcoming_dict.values())

    def _past_sort_key(self, game_dict: dict) -> str:
        """past 정렬용 종료일 키 (누락 시 빈 문자열)"""
        return game_dict.get("freePeriod", {}).get("end", "")
