import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.domain.entities.game import Game
from src.domain.ports.game_repository import GameRepository
from src.application.use_cases.save_games import SaveGamesUseCase
from src.domain.value_objects.free_period import FreePeriod
from src.domain.value_objects.genre import Genre

logger = logging.getLogger(__name__)


class JsonFileRepository(GameRepository):
    """JSON 파일로 게임 목록을 저장하는 Repository (누적 저장 지원)"""

    def __init__(self, output_path: Path):
        self.output_path = output_path

    def save(self, games: list[Game]) -> None:
        """게임 목록을 JSON 파일로 저장 (기존 데이터와 병합)"""
        logger.info(f"Saving {len(games)} games")
        existing_data = self._load_existing_data()
        output_data = SaveGamesUseCase(self._game_to_dict).execute(games, existing_data)
        self._write_to_file(output_data)

    def _write_to_file(self, output_data: dict) -> None:
        """데이터를 JSON 파일로 원자적으로 저장 (위험 2 방어: 파일 쓰기 중 실패 시 손상 방지)"""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 임시 파일에 먼저 쓰기
        temp_path = self.output_path.with_suffix('.tmp')
        try:
            temp_path.write_text(
                json.dumps(output_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            # 원자적 rename (성공 시에만 원본 파일 교체)
            temp_path.rename(self.output_path)
            logger.info(f"Successfully saved data to {self.output_path}")
        except Exception as e:
            logger.error(f"Failed to write data to {self.output_path}: {e}")
            # 임시 파일 정리
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _load_existing_data(self) -> dict:
        """기존 JSON 파일 로드 및 데이터 구조 검증"""
        if self.output_path.exists():
            try:
                data = json.loads(self.output_path.read_text(encoding="utf-8"))

                # 데이터 구조 검증
                if not isinstance(data, dict):
                    return {}

                # 필수 키가 없으면 빈 리스트로 초기화
                if "past" not in data or not isinstance(data["past"], list):
                    data["past"] = []
                if "currentFree" not in data or not isinstance(data["currentFree"], list):
                    data["currentFree"] = []

                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load existing data from {self.output_path}: {e}")
                return {}
        return {}

    def _game_to_dict(self, game: Game) -> dict:
        """Game 엔티티를 딕셔너리로 변환"""
        game_dict = {
            "id": game.id,
            "slug": game.slug,
            "namespace": game.namespace,
            "title": game.title,
            "thumbnail": game.thumbnail,
            "epicUrl": game.epic_url,
            "freePeriod": {
                "start": game.free_period.start.isoformat(),
                "end": game.free_period.end.isoformat(),
            },
            "genres": [{"id": genre.id, "name": genre.name} for genre in game.genres],
        }

        if game.rating:
            game_dict["rating"] = {
                "epic": game.rating.epic,
                "metacritic": game.rating.metacritic,
                "opencritic": game.rating.opencritic,
                "steam": game.rating.steam,
                "scoreColor": game.rating.score_color(),
            }

        return game_dict

    def _dict_to_game(self, game_dict: dict) -> Game | None:
        """딕셔너리를 Game 엔티티로 변환"""
        try:
            free_period_data = game_dict.get("freePeriod", {})
            free_period = FreePeriod(
                start=datetime.fromisoformat(free_period_data.get("start", "2000-01-01T00:00:00+00:00")),
                end=datetime.fromisoformat(free_period_data.get("end", "2000-01-01T00:00:00+00:00")),
            )

            genres = [
                Genre(id=g.get("id", 0), name=g.get("name", ""))
                for g in game_dict.get("genres", [])
            ]

            return Game(
                id=game_dict.get("id", ""),
                slug=game_dict.get("slug", ""),
                namespace=game_dict.get("namespace", ""),
                title=game_dict.get("title", ""),
                thumbnail=game_dict.get("thumbnail", ""),
                epic_url=game_dict.get("epicUrl", ""),
                free_period=free_period,
                genres=genres,
                rating=None,
            )
        except Exception:
            return None

    def load_past_games_without_rating(self) -> list[Game]:
        """rating이 없는 past 게임 로드"""
        data = self._load_existing_data()
        past_games = []

        for game_dict in data.get("past", []):
            if game_dict.get("rating"):
                continue
            game = self._dict_to_game(game_dict)
            if game:
                past_games.append(game)

        return past_games

    def update_past_ratings(self, enriched_games: list[Game]) -> int:
        """past 게임의 rating 업데이트"""
        if not enriched_games:
            return 0

        data = self._load_existing_data()
        enriched_map = {g.id: g for g in enriched_games if g.rating}

        updated_count = 0
        for game_dict in data.get("past", []):
            game_id = game_dict.get("id")
            if game_id in enriched_map:
                rating = enriched_map[game_id].rating
                game_dict["rating"] = {
                    "metacritic": rating.metacritic,
                    "epic": rating.epic,
                    "opencritic": rating.opencritic,
                    "steam": rating.steam,
                    "scoreColor": rating.score_color(),
                }
                updated_count += 1

        if updated_count > 0:
            data["updated"] = datetime.now(timezone.utc).isoformat()
            self._write_to_file(data)

        return updated_count
