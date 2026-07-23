from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from app.models.api_schemas import ResearchCardOut
from app.research import all_research_cards, get_research_card

router = APIRouter(tags=["research"])


@router.get("/research", response_model=List[ResearchCardOut])
def research_all() -> List[ResearchCardOut]:
    return [
        ResearchCardOut(
            metric_name=c.metric_name, definition=c.definition, research_basis=c.research_basis,
            calculation=c.calculation, evidence=c.evidence, confidence_notes=c.confidence_notes,
            limitations=c.limitations, is_original_to_bpm=c.is_original_to_bpm,
        )
        for c in all_research_cards().values()
    ]


@router.get("/research/{metric_name}", response_model=ResearchCardOut)
def research_one(metric_name: str) -> ResearchCardOut:
    card = get_research_card(metric_name)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No research card for '{metric_name}'.")
    return ResearchCardOut(
        metric_name=card.metric_name, definition=card.definition, research_basis=card.research_basis,
        calculation=card.calculation, evidence=card.evidence, confidence_notes=card.confidence_notes,
        limitations=card.limitations, is_original_to_bpm=card.is_original_to_bpm,
    )
