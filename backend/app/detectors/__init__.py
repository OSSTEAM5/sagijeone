"""탐지기 모듈을 import하는 순간 @detector가 실행되어 등록됩니다.
(4강: 데코레이터는 함수 호출 시점이 아니라 모듈이 import될 때 실행됨)

새 탐지기 파일을 만들면 아래에 import 한 줄만 추가하세요.
"""
from app.detectors import payment, url  # noqa: F401
from app.detectors.registry import detectors  # noqa: F401
