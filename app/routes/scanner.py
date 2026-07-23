from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from app.models.api_schemas import RankedSymbolOut, ranked_symbol_to_api
from app.ranking_cache import ranking_cache

router = APIRouter(prefix="/scanner", tags=["scanner"])


@router.get("/top", response_model=List[RankedSymbolOut])
def scanner_top(limit: int = Query(20, ge=1, le=200)) -> List[RankedSymbolOut]:
    results = ranking_cache.get()[:limit]
    return [ranked_symbol_to_api(r) for r in results]


@router.get("/ticker/{symbol}", response_model=RankedSymbolOut)
def scanner_ticker(symbol: str) -> RankedSymbolOut:
    result = ranking_cache.get_for_symbol(symbol.upper())
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"No current ranking for '{symbol}' — it may not be in the qualified universe.")
    return ranked_symbol_to_api(result)
