from __future__ import annotations

from typing import Any


class MacroDataService:
    """금리·환율·지수 등 거시 지표 (FRED / 한국은행 ECOS 연동 예정)."""

    def get_macro_snapshot(self, market: str = "KR") -> dict[str, Any]:
        raise NotImplementedError("MacroDataService.get_macro_snapshot() 미구현")
