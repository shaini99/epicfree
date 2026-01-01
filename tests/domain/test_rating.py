"""Rating Value Object 테스트"""

import pytest

from src.domain.value_objects.rating import Rating, RATING_SOURCE_CONFIGS


class TestRatingValidation:
    """검증 로직 테스트"""

    def test_valid_metacritic_score(self):
        """유효한 Metacritic 점수 생성"""
        rating = Rating(metacritic=85)
        assert rating.metacritic == 85

    def test_invalid_metacritic_below_range(self):
        """Metacritic 점수가 0 미만일 때 예외"""
        with pytest.raises(ValueError, match="metacritic must be"):
            Rating(metacritic=-1)

    def test_invalid_metacritic_above_range(self):
        """Metacritic 점수가 100 초과일 때 예외"""
        with pytest.raises(ValueError, match="metacritic must be"):
            Rating(metacritic=101)

    def test_none_scores_allowed(self):
        """None 점수 허용"""
        rating = Rating(metacritic=None)
        assert rating.metacritic is None


class TestScoreColor:
    """색상 분류 테스트"""

    def test_excellent_score_returns_green(self):
        """75점 이상은 green"""
        rating = Rating(metacritic=75)
        assert rating.score_color() == "green"

        rating = Rating(metacritic=100)
        assert rating.score_color() == "green"

    def test_good_score_returns_yellow(self):
        """50-74점은 yellow"""
        rating = Rating(metacritic=50)
        assert rating.score_color() == "yellow"

        rating = Rating(metacritic=74)
        assert rating.score_color() == "yellow"

    def test_poor_score_returns_red(self):
        """50점 미만은 red"""
        rating = Rating(metacritic=49)
        assert rating.score_color() == "red"

        rating = Rating(metacritic=0)
        assert rating.score_color() == "red"

    def test_no_metacritic_uses_aggregate(self):
        """Metacritic 없으면 aggregate 사용"""
        rating = Rating(opencritic=80)
        assert rating.score_color() == "green"


class TestHasRating:
    """평점 존재 여부 테스트"""

    def test_has_rating_with_metacritic(self):
        """Metacritic만 있어도 True"""
        rating = Rating(metacritic=80)
        assert rating.has_rating() is True

    def test_has_rating_with_steam(self):
        """Steam만 있어도 True"""
        rating = Rating(steam=80)
        assert rating.has_rating() is True

    def test_has_no_rating(self):
        """둘 다 없으면 False"""
        rating = Rating()
        assert rating.has_rating() is False


class TestNormalization:
    """정규화 테스트"""

    def test_metacritic_normalization(self):
        """Metacritic은 그대로 (0-100)"""
        rating = Rating(metacritic=75)
        normalized = rating.get_all_scores_normalized()
        assert normalized["metacritic"] == 75.0

    def test_steam_normalization(self):
        """Steam은 0-100 유지"""
        rating = Rating(steam=80)
        normalized = rating.get_all_scores_normalized()
        assert normalized["steam"] == 80.0

    def test_all_scores_normalized(self):
        """모든 점수 정규화"""
        rating = Rating(metacritic=80, steam=80)
        normalized = rating.get_all_scores_normalized()
        assert normalized["metacritic"] == 80.0
        assert normalized["steam"] == 80.0


class TestAggregateScore:
    """종합 점수 계산 테스트"""

    def test_aggregate_with_equal_weights(self):
        """동일 가중치 평균"""
        rating = Rating(metacritic=80, steam=80)
        assert rating.aggregate_score() == 80.0

    def test_aggregate_with_custom_weights(self):
        """커스텀 가중치 평균"""
        rating = Rating(metacritic=100, steam=50)
        # metacritic 가중치 3, steam 가중치 1
        weights = {"metacritic": 3.0, "steam": 1.0}
        # (100*3 + 50*1) / 4 = 87.5
        assert rating.aggregate_score(weights) == 87.5

    def test_aggregate_no_scores(self):
        """점수 없으면 0"""
        rating = Rating()
        assert rating.aggregate_score() == 0.0


class TestGetAllScores:
    """점수 조회 테스트"""

    def test_get_all_scores(self):
        """모든 점수 딕셔너리로 반환"""
        rating = Rating(metacritic=85, steam=81)
        scores = rating.get_all_scores()
        assert scores["metacritic"] == 85
        assert scores["steam"] == 81

    def test_get_all_scores_excludes_none(self):
        """None 값은 제외"""
        rating = Rating(metacritic=85)
        scores = rating.get_all_scores()
        assert "metacritic" in scores
        assert "steam" not in scores

    def test_registry_contains_configs(self):
        """레지스트리에 설정 등록됨"""
        assert "metacritic" in RATING_SOURCE_CONFIGS
        assert "steam" in RATING_SOURCE_CONFIGS


class TestAdditionalSources:
    """추가 소스 테스트 (확장성)"""

    def test_has_rating_with_additional_sources(self):
        """추가 소스만 있어도 True"""
        # 참고: 아직 등록되지 않은 소스는 검증되지 않음
        rating = Rating(additional_sources={"custom": 75.0})
        assert rating.has_rating() is True

    def test_get_all_scores_includes_additional(self):
        """추가 소스도 포함"""
        rating = Rating(metacritic=80, additional_sources={"custom": 75.0})
        scores = rating.get_all_scores()
        assert scores["metacritic"] == 80
        assert scores["custom"] == 75.0
