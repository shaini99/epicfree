from dataclasses import dataclass, field
from typing import Callable


# === 등급 임계값 상수 ===
EXCELLENT_THRESHOLD = 75
GOOD_THRESHOLD = 50


# === 점수 소스 설정 (확장 가능) ===
def _normalize_ratio(value: float, max_value: float) -> float:
    return (value / max_value) * 100


RATING_SOURCE_CONFIGS: dict[str, dict[str, float | Callable]] = {
    "epic": {"min": 0.0, "max": 5.0, "normalize": lambda v: _normalize_ratio(v, 5.0)},
    "metacritic": {"min": 0.0, "max": 100.0, "normalize": lambda v: v},
    "opencritic": {"min": 0.0, "max": 100.0, "normalize": lambda v: v},
    "steam": {"min": 0.0, "max": 100.0, "normalize": lambda v: v},
}


def _validate_score(source_name: str, value: float) -> bool:
    config = RATING_SOURCE_CONFIGS.get(source_name)
    if not config:
        return True
    return config["min"] <= value <= config["max"]


def _normalize_score(source_name: str, value: float) -> float:
    config = RATING_SOURCE_CONFIGS.get(source_name)
    if not config:
        return value
    normalize = config["normalize"]
    return normalize(value)


@dataclass(frozen=True)
class Rating:
    """게임 평점을 나타내는 Value Object (확장 가능한 하이브리드 구조)"""

    # 주요 필드 (E, M, O, S)
    epic: float | None = None  # 0-5 (Epic 유저 평점)
    metacritic: int | None = None  # 0-100
    opencritic: int | None = None  # 0-100
    steam: int | None = None  # 0-100 (Steam 긍정 평가 비율)

    # 확장 가능한 추가 소스 (선택)
    additional_sources: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        # 각 필드 검증
        fields_to_validate = [
            ("epic", self.epic),
            ("metacritic", self.metacritic),
            ("opencritic", self.opencritic),
            ("steam", self.steam),
        ]

        for field_name, value in fields_to_validate:
            if value is not None:
                if not _validate_score(field_name, value):
                    config = RATING_SOURCE_CONFIGS.get(field_name)
                    min_value = config["min"] if config else None
                    max_value = config["max"] if config else None
                    raise ValueError(
                        f"{field_name} must be {min_value}-{max_value}: {value}"
                    )

        # 추가 소스 검증
        for source_name, value in self.additional_sources.items():
            if not _validate_score(source_name, value):
                config = RATING_SOURCE_CONFIGS.get(source_name)
                min_value = config["min"] if config else None
                max_value = config["max"] if config else None
                raise ValueError(
                    f"{source_name} must be {min_value}-{max_value}: {value}"
                )

    def get_all_scores(self) -> dict[str, float]:
        """모든 점수를 딕셔너리로 반환"""
        result = {}

        # 주요 필드 (E, M, O, S)
        if self.epic is not None:
            result["epic"] = self.epic
        if self.metacritic is not None:
            result["metacritic"] = self.metacritic
        if self.opencritic is not None:
            result["opencritic"] = self.opencritic
        if self.steam is not None:
            result["steam"] = self.steam

        # deprecated 필드
        result.update(self.additional_sources)
        return result

    def get_all_scores_normalized(self) -> dict[str, float]:
        """모든 점수를 0-100 스케일로 정규화하여 반환"""
        result = {}

        fields = [
            ("epic", self.epic),
            ("metacritic", self.metacritic),
            ("opencritic", self.opencritic),
            ("steam", self.steam),
        ]

        for field_name, value in fields:
            if value is not None:
                result[field_name] = _normalize_score(field_name, value)

        for source_name, value in self.additional_sources.items():
            result[source_name] = _normalize_score(source_name, value)

        return result

    def aggregate_score(self, weights: dict[str, float] | None = None) -> float:
        """가중 평균 점수 계산"""
        normalized = self.get_all_scores_normalized()

        if not normalized:
            return 0.0

        if weights is None:
            # 기본: 동일 가중치
            weights = {k: 1.0 for k in normalized}

        total_weight = sum(weights.get(k, 0.0) for k in normalized)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(
            score * weights.get(source, 0.0)
            for source, score in normalized.items()
        )

        return weighted_sum / total_weight

    def score_color(self) -> str:
        """종합 점수에 따른 색상 분류 (0-100 스케일 기준)"""
        # 우선순위: opencritic → metacritic → steam → aggregate
        if self.opencritic is not None:
            score = self.opencritic
        elif self.metacritic is not None:
            score = self.metacritic
        elif self.steam is not None:
            score = self.steam
        else:
            score = self.aggregate_score()

        if score >= EXCELLENT_THRESHOLD:
            return "green"
        if score >= GOOD_THRESHOLD:
            return "yellow"
        return "red"

    def has_rating(self) -> bool:
        """평점 정보가 존재하는지 확인"""
        return (
            self.epic is not None
            or self.metacritic is not None
            or self.opencritic is not None
            or self.steam is not None
            or len(self.additional_sources) > 0
        )
