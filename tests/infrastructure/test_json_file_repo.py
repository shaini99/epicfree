"""JsonFileRepository 단위 테스트"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.domain.entities.game import Game
from src.domain.value_objects.free_period import FreePeriod
from src.infrastructure.repositories.json_file_repo import JsonFileRepository


class TestLoadExistingData:
    """_load_existing_data 메서드 테스트"""

    def test_load_when_file_does_not_exist(self, temp_json_file: Path):
        """파일이 없으면 빈 딕셔너리 반환"""
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert result == {}

    def test_load_valid_json_data(self, temp_json_file: Path, sample_json_data: dict[str, Any]):
        """유효한 JSON 데이터 로드"""
        temp_json_file.write_text(json.dumps(sample_json_data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert "updated" in result
        assert "currentFree" in result
        assert "past" in result
        assert len(result["currentFree"]) == 1
        assert len(result["past"]) == 1

    def test_load_handles_json_decode_error(self, temp_json_file: Path):
        """JSON 파싱 에러 시 빈 딕셔너리 반환"""
        temp_json_file.write_text("invalid json{", encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert result == {}

    def test_load_handles_io_error(self, temp_json_file: Path):
        """파일 읽기 에러 시 빈 딕셔너리 반환"""
        repo = JsonFileRepository(temp_json_file)

        with patch.object(Path, 'read_text', side_effect=IOError("File error")):
            result = repo._load_existing_data()

        assert result == {}

    def test_load_initializes_missing_keys(self, temp_json_file: Path):
        """필수 키가 없으면 빈 리스트로 초기화"""
        # past와 currentFree가 없는 데이터
        invalid_data = {
            "updated": "2025-01-01T00:00:00+00:00"
        }
        temp_json_file.write_text(json.dumps(invalid_data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert result["past"] == []
        assert result["currentFree"] == []

    def test_load_validates_game_data_structure(self, temp_json_file: Path):
        """잘못된 게임 데이터가 있어도 그대로 로드"""
        data = {
            "currentFree": [
                {
                    "id": "valid-game",
                    "freePeriod": {
                        "start": "2025-01-01T00:00:00+00:00",
                        "end": "2025-01-08T00:00:00+00:00"
                    }
                },
                {
                    "id": "invalid-game"
                    # freePeriod 누락
                }
            ],
            "past": []
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert len(result["currentFree"]) == 2
        assert result["currentFree"][0]["id"] == "valid-game"
        assert result["currentFree"][1]["id"] == "invalid-game"

    def test_load_handles_non_dict_data(self, temp_json_file: Path):
        """딕셔너리가 아닌 데이터는 빈 딕셔너리 반환"""
        temp_json_file.write_text(json.dumps(["array", "data"]), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert result == {}

    def test_load_handles_non_list_values(self, temp_json_file: Path):
        """past/currentFree가 리스트가 아니면 빈 리스트로 초기화"""
        data = {
            "past": "not-a-list",
            "currentFree": {"not": "a-list"}
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        result = repo._load_existing_data()

        assert result["past"] == []
        assert result["currentFree"] == []


class TestSave:
    """save 메서드 테스트"""

    def test_save_creates_output_directory(self, tmp_path: Path):
        """저장 시 출력 디렉토리 생성"""
        output_path = tmp_path / "nested" / "dir" / "games.json"
        repo = JsonFileRepository(output_path)

        repo.save([])

        assert output_path.parent.exists()

    def test_save_current_free_games(self, temp_json_file: Path, sample_game: Game):
        """현재 무료 게임 저장"""
        repo = JsonFileRepository(temp_json_file)

        # 현재 무료인 게임
        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([sample_game])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        assert len(data["currentFree"]) == 1
        assert data["currentFree"][0]["id"] == "test-game-id"
        assert len(data["upcoming"]) == 0

    def test_save_upcoming_games(self, temp_json_file: Path):
        """예정된 무료 게임 저장"""
        repo = JsonFileRepository(temp_json_file)

        upcoming_game = Game(
            id="upcoming-id",
            slug="upcoming-slug",
            namespace="upcoming-namespace",
            title="Upcoming Game",
            thumbnail="thumbnail.jpg",
            epic_url="https://store.epicgames.com/ko/p/upcoming",
            free_period=FreePeriod(
                start=datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 2, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.entities.game.Game.is_currently_free', return_value=False):
            with patch('src.domain.entities.game.Game.is_upcoming', return_value=True):
                repo.save([upcoming_game])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        assert len(data["upcoming"]) == 1
        assert data["upcoming"][0]["id"] == "upcoming-id"
        assert len(data["currentFree"]) == 0

    def test_save_merges_with_existing_data(self, temp_json_file: Path, sample_json_data: dict[str, Any]):
        """기존 데이터와 병합하여 저장"""
        # 기존 데이터 저장
        temp_json_file.write_text(json.dumps(sample_json_data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        # 새 게임 추가
        new_game = Game(
            id="new-game-id",
            slug="new-slug",
            namespace="new-namespace",
            title="New Game",
            thumbnail="new.jpg",
            epic_url="https://store.epicgames.com/ko/p/new",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([new_game])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        # 새 게임이 추가됨
        assert len(data["currentFree"]) == 1
        assert data["currentFree"][0]["id"] == "new-game-id"

        # 기존 past 데이터는 유지되고, 기존 currentFree 게임도 past로 이동
        # (기존 past 1개 + 이동된 currentFree 1개 = 2개)
        assert len(data["past"]) == 2

    def test_save_moves_expired_games_to_past(self, temp_json_file: Path, sample_json_data: dict[str, Any]):
        """무료 기간이 끝난 게임을 past로 이동"""
        # 기존 데이터 저장
        temp_json_file.write_text(json.dumps(sample_json_data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        # 빈 리스트로 저장 (기존 currentFree 게임들이 없어짐)
        repo.save([])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        # currentFree가 비었고, past에 이동됨
        assert len(data["currentFree"]) == 0
        # 기존 past(1) + 이동된 게임(1) = 2
        assert len(data["past"]) == 2

    def test_save_sorts_past_games_by_end_date(self, temp_json_file: Path):
        """past 게임들을 종료일 기준 내림차순 정렬"""
        repo = JsonFileRepository(temp_json_file)

        # 여러 기간의 게임 생성
        game1 = Game(
            id="game-1",
            slug="slug-1",
            namespace="ns-1",
            title="Game 1",
            thumbnail="thumb1.jpg",
            epic_url="url1",
            free_period=FreePeriod(
                start=datetime(2024, 12, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2024, 12, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        game2 = Game(
            id="game-2",
            slug="slug-2",
            namespace="ns-2",
            title="Game 2",
            thumbnail="thumb2.jpg",
            epic_url="url2",
            free_period=FreePeriod(
                start=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2024, 11, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        # 먼저 game1 저장 후 past로 이동
        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([game1])

        # game2 저장 (game1은 past로 이동)
        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([game2])

        # 모두 past로 이동
        repo.save([])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        # 최신 종료일이 먼저 (game1 > game2)
        assert data["past"][0]["id"] == "game-1"
        assert data["past"][1]["id"] == "game-2"

    def test_save_includes_updated_timestamp(self, temp_json_file: Path):
        """저장 시 updated 타임스탬프 포함"""
        repo = JsonFileRepository(temp_json_file)

        repo.save([])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        assert "updated" in data
        # ISO 8601 형식 검증
        updated_time = datetime.fromisoformat(data["updated"])
        assert updated_time.tzinfo == timezone.utc

    def test_save_includes_rating_when_present(self, temp_json_file: Path, sample_game_with_rating: Game):
        """평점이 있는 경우 rating 포함하여 저장"""
        repo = JsonFileRepository(temp_json_file)

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([sample_game_with_rating])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        assert "rating" in data["currentFree"][0]
        rating = data["currentFree"][0]["rating"]
        assert rating["epic"] == 4.5
        assert rating["metacritic"] == 85
        assert rating["opencritic"] == 88
        assert rating["scoreColor"] == "green"

    def test_save_handles_invalid_existing_data_gracefully(self, temp_json_file: Path):
        """기존 데이터가 잘못되어도 계속 진행"""
        # 잘못된 날짜 형식의 데이터
        invalid_data = {
            "currentFree": [
                {
                    "id": "bad-game",
                    "freePeriod": {
                        "start": "invalid-date",
                        "end": "2025-01-08T00:00:00+00:00"
                    }
                }
            ],
            "past": []
        }
        temp_json_file.write_text(json.dumps(invalid_data), encoding="utf-8")
        repo = JsonFileRepository(temp_json_file)

        # 에러 없이 저장 완료되어야 함
        repo.save([])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))
        assert "updated" in data

    def test_save_writes_utf8_encoding(self, temp_json_file: Path):
        """UTF-8 인코딩으로 저장 (한글 지원)"""
        repo = JsonFileRepository(temp_json_file)

        korean_game = Game(
            id="korean-game",
            slug="korean-slug",
            namespace="korean-namespace",
            title="한글 게임 제목",
            thumbnail="thumb.jpg",
            epic_url="url",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([korean_game])

        # UTF-8로 읽어서 한글이 정상적으로 읽히는지 확인
        content = temp_json_file.read_text(encoding="utf-8")
        assert "한글 게임 제목" in content

        data = json.loads(content)
        assert data["currentFree"][0]["title"] == "한글 게임 제목"


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_duplicate_game_in_api_response(self, temp_json_file: Path):
        """API가 중복 게임을 반환해도 중복 저장되지 않아야 함"""
        repo = JsonFileRepository(temp_json_file)

        # 동일한 ID를 가진 게임 2개 생성
        game1 = Game(
            id="duplicate-game",
            slug="slug-1",
            namespace="ns-dup-1",
            title="Game Title 1",
            thumbnail="thumb1.jpg",
            epic_url="url1",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        game2 = Game(
            id="duplicate-game",  # 동일 ID
            slug="slug-2",
            namespace="ns-dup-2",
            title="Game Title 2",  # 다른 내용
            thumbnail="thumb2.jpg",
            epic_url="url2",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([game1, game2])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        # 중복 제거되어 1개만 저장되어야 함
        assert len(data["currentFree"]) == 1
        assert data["currentFree"][0]["id"] == "duplicate-game"
        # 마지막 게임 (game2)의 정보가 저장됨
        assert data["currentFree"][0]["title"] == "Game Title 2"

    def test_reappeared_game_removed_from_past(self, temp_json_file: Path):
        """과거 무료 게임이 다시 무료가 되면 past에서 제거되어야 함"""
        repo = JsonFileRepository(temp_json_file)

        # 1단계: 게임 저장
        game = Game(
            id="reappearing-game",
            slug="reappearing-slug",
            namespace="reappearing-ns",
            title="Reappearing Game",
            thumbnail="thumb.jpg",
            epic_url="url",
            free_period=FreePeriod(
                start=datetime(2024, 12, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2024, 12, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([game])

        # 2단계: 게임을 past로 이동 (빈 리스트로 저장)
        repo.save([])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))
        assert len(data["past"]) == 1
        assert data["past"][0]["id"] == "reappearing-game"
        assert len(data["currentFree"]) == 0

        # 3단계: 같은 게임이 다시 무료로 등장
        new_game = Game(
            id="reappearing-game",  # 동일 ID
            slug="reappearing-slug",
            namespace="reappearing-ns",
            title="Reappearing Game",
            thumbnail="thumb.jpg",
            epic_url="url",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([new_game])

        data = json.loads(temp_json_file.read_text(encoding="utf-8"))

        # currentFree에 추가되고 past에서는 제거되어야 함
        assert len(data["currentFree"]) == 1
        assert data["currentFree"][0]["id"] == "reappearing-game"
        assert len(data["past"]) == 0

    def test_atomic_write_on_failure(self, temp_json_file: Path):
        """파일 쓰기 실패 시 기존 파일이 손상되지 않아야 함"""
        repo = JsonFileRepository(temp_json_file)

        # 1단계: 기존 데이터 저장
        initial_game = Game(
            id="initial-game",
            slug="initial-slug",
            namespace="initial-namespace",
            title="Initial Game",
            thumbnail="thumb.jpg",
            epic_url="url",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
            repo.save([initial_game])

        # 기존 파일 내용 저장
        original_content = temp_json_file.read_text(encoding="utf-8")
        original_data = json.loads(original_content)
        assert original_data["currentFree"][0]["id"] == "initial-game"

        # 2단계: 쓰기 실패 시뮬레이션 (write_text가 실패하도록 mock)
        new_game = Game(
            id="new-game",
            slug="new-slug",
            namespace="new-namespace",
            title="New Game",
            thumbnail="thumb.jpg",
            epic_url="url",
            free_period=FreePeriod(
                start=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                end=datetime(2025, 1, 8, 0, 0, 0, tzinfo=timezone.utc)
            ),
            genres=[]
        )

        with patch('pathlib.Path.write_text', side_effect=IOError("Disk full")):
            with pytest.raises(IOError):
                with patch('src.domain.value_objects.free_period.FreePeriod.is_active', return_value=True):
                    repo.save([new_game])

        # 3단계: 기존 파일이 손상되지 않았는지 확인
        current_content = temp_json_file.read_text(encoding="utf-8")
        current_data = json.loads(current_content)

        # 기존 데이터가 그대로 유지되어야 함
        assert current_content == original_content
        assert current_data["currentFree"][0]["id"] == "initial-game"

        # 임시 파일이 정리되었는지 확인
        temp_file = temp_json_file.with_suffix('.tmp')
        assert not temp_file.exists()
