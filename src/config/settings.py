from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 웹 데이터 경로
WEB_DATA_PATH = PROJECT_ROOT / "web" / "data"

# JSON 출력 파일 경로
OUTPUT_JSON_PATH = WEB_DATA_PATH / "games-free.json"
