import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .arcgis_client import ArcgisParcelClient
from .bylaw_loader import naive_search_bylaw
from .llm_client import generate_llm_answer
from .models import (
    BylawAnswer,
    ParcelInfo,
    PropertyAnalysisResponse,
    PropertyQueryRequest,
)

load_dotenv()

app = FastAPI(
    title="Nanaimo Property Insights API",
    description=(
        "Takes a Nanaimo, BC address, looks up parcel information from the "
        "City's GIS service, and then uses key Nanaimo bylaws (zoning, "
        "building, parking, fees, etc.) to surface potentially relevant "
        "regulations."
    ),
    version="0.1.0",
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_arcgis_client() -> ArcgisParcelClient:
    return ArcgisParcelClient()


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=PropertyAnalysisResponse, tags=["analysis"])
def analyze_property(
    payload: PropertyQueryRequest,
    arcgis: ArcgisParcelClient = Depends(get_arcgis_client),
) -> PropertyAnalysisResponse:
    """
    Main entrypoint: given an address (and optional question), return parcel data
    plus some bylaw passages that may be relevant.
    """
    parcel: Optional[ParcelInfo] = arcgis.search_parcel_by_address(payload.address)

    bylaw_answer: Optional[BylawAnswer] = None
    if payload.question:
        bylaw_answer = naive_search_bylaw(payload.question)

    llm_answer: Optional[str] = None
    if payload.question:
        llm_answer = generate_llm_answer(
            address=payload.address,
            question=payload.question,
            parcel=parcel,
            bylaw_answer=bylaw_answer,
        )

    return PropertyAnalysisResponse(
        address=payload.address,
        parcel=parcel,
        bylaw_answer=bylaw_answer,
        llm_answer=llm_answer,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )

