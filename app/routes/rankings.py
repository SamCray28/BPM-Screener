from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.models.api_schemas import RankedSymbolOut, ranked_symbol_to_api
from app.ranking_cache import ranking_cache

router = APIRouter(tags=["rankings"])


@router.get("/rankings", response_model=List[RankedSymbolOut])
def rankings() -> List[RankedSymbolOut]:
    return [ranked_symbol_to_api(r) for r in ranking_cache.get()]
