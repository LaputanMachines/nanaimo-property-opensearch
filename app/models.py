from typing import Optional, List

from pydantic import BaseModel, Field


class PropertyQueryRequest(BaseModel):
    address: str = Field(..., description="Street address in Nanaimo, BC")
    question: Optional[str] = Field(
        None,
        description="Optional natural-language question about what can be done with this property",
    )


class ParcelGeometry(BaseModel):
    wkid: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None


class ParcelAttributes(BaseModel):
    object_id: Optional[int] = Field(None, alias="OBJECTID")
    civic_address: Optional[str] = None
    folio: Optional[str] = None
    zoning: Optional[str] = None
    lot_area_sq_m: Optional[float] = None
    raw: dict = Field(default_factory=dict, description="Full attribute payload from ArcGIS")


class ParcelInfo(BaseModel):
    attributes: ParcelAttributes
    geometry: Optional[ParcelGeometry] = None
    arcgis_feature_id: Optional[int] = None


class BylawExcerpt(BaseModel):
    source: str
    heading: Optional[str] = None
    snippet: str


class BylawAnswer(BaseModel):
    summary: str
    excerpts: List[BylawExcerpt] = Field(default_factory=list)


class PropertyAnalysisResponse(BaseModel):
    address: str
    parcel: Optional[ParcelInfo] = None
    bylaw_answer: Optional[BylawAnswer] = None
    llm_answer: Optional[str] = Field(
        default=None,
        description="Natural-language answer generated from parcel + bylaw context, if LLM is configured.",
    )
