import os
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import requests
from fastapi import HTTPException, status
from pypdf import PdfReader

from .models import BylawAnswer, BylawExcerpt

DATA_DIR = Path(os.getenv("NANAIMO_BYLAW_DATA_DIR", "data")).resolve()

# Core building-related bylaws listed at:
# https://www.nanaimo.ca/property-development/building-permits/bylaws-for-building
BYLAWS: List[Dict[str, Any]] = [
    {
        "id": "zoning_4500",
        "name": "Zoning Bylaw No. 4500",
        "url": os.getenv(
            "NANAIMO_ZONING_BYLAW_URL",
            "https://www.nanaimo.ca/ByLaws/ViewBylaw/4500.pdf",
        ),
        "filename": "zoning_bylaw_4500.pdf",
    },
    {
        "id": "building_7224",
        "name": "Building Bylaw No. 7224",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/7224.pdf",
        "filename": "building_bylaw_7224.pdf",
    },
    {
        "id": "off_street_parking_7266",
        "name": "Off-Street Parking Regulations Bylaw No. 7266",
        "url": "https://www.nanaimo.ca/bylaws/ViewBylaw/7266.pdf",
        "filename": "off_street_parking_regulations_bylaw_7266.pdf",
    },
    {
        "id": "fees_and_charges_7336",
        "name": "Fees and Charges Bylaw No. 7336",
        "url": "https://www.nanaimo.ca/bylaws/ViewBylaw/7336.pdf",
        "filename": "fees_and_charges_bylaw_7336.pdf",
    },
    {
        "id": "dcc_7252",
        "name": "Development Cost Charge Bylaw No. 7252",
        "url": "https://www.nanaimo.ca/docs/your-government/projects/2016-dcc-review/dcc-bylaw-2017-no-7252.pdf",
        "filename": "development_cost_charge_bylaw_7252.pdf",
    },
    {
        "id": "sign_2850",
        "name": "Sign Bylaw No. 2850",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/2850.pdf",
        "filename": "sign_bylaw_2850.pdf",
    },
    {
        "id": "subdivision_control_3260",
        "name": "Subdivision Control Bylaw No. 3260",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/3260.pdf",
        "filename": "subdivision_control_bylaw_3260.pdf",
    },
    {
        "id": "trees_7126",
        "name": "Management and Protection of Trees Bylaw No. 7126",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/7126.pdf",
        "filename": "management_and_protection_of_trees_bylaw_7126.pdf",
    },
    {
        "id": "waterworks_7004",
        "name": "Waterworks Rate and Regulation Bylaw No. 7004",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/7004.pdf",
        "filename": "waterworks_rate_and_regulation_bylaw_7004.pdf",
    },
    {
        "id": "storm_sewer_7351",
        "name": "Storm Sewer Regulation and Charge Bylaw No. 7351",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/7351.pdf",
        "filename": "storm_sewer_regulation_and_charge_bylaw_7351.pdf",
    },
    {
        "id": "sewer_2496",
        "name": "Sewer Regulation and Charge Bylaw No. 2496",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/2496.pdf",
        "filename": "sewer_regulation_and_charge_bylaw_2496.pdf",
    },
    {
        "id": "soil_1747",
        "name": "Soil Removal and Depositing Bylaw No. 1747",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/1747.pdf",
        "filename": "soil_removal_and_depositing_bylaw_1747.pdf",
    },
    {
        "id": "heritage_procedures_5549",
        "name": "Heritage Procedures Bylaw No. 5549",
        "url": "https://www.nanaimo.ca/ByLaws/ViewBylaw/5549.pdf",
        "filename": "heritage_procedures_bylaw_5549.pdf",
    },
    {
        "id": "business_licence_7318",
        "name": "Business Licence Bylaw No. 7318",
        "url": "https://www.nanaimo.ca/bylaws/ViewBylaw/7318.pdf",
        "filename": "business_licence_bylaw_7318.pdf",
    },
]


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_bylaw_config(bylaw_id: str) -> Dict[str, Any]:
    for cfg in BYLAWS:
        if cfg["id"] == bylaw_id:
            return cfg
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unknown bylaw id: {bylaw_id}",
    )


def _download_bylaw_pdf(config: Dict[str, Any]) -> Path:
    _ensure_data_dir()
    pdf_path = DATA_DIR / config["filename"]
    if pdf_path.exists():
        return pdf_path

    url = config["url"]
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download bylaw '{config['name']}' from {url}: {exc}",
        ) from exc

    pdf_path.write_bytes(resp.content)
    return pdf_path


def _extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages_text: List[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:  # pypdf is permissive; ignore per-page errors
            txt = ""
        pages_text.append(txt)
    return "\n".join(pages_text)


def _split_into_paragraphs(text: str) -> List[str]:
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    paragraphs: List[str] = []
    for p in raw_paragraphs:
        wrapped = textwrap.fill(p, width=1000)
        paragraphs.append(wrapped)
    return paragraphs


@lru_cache(maxsize=None)
def _load_bylaw_paragraphs(bylaw_id: str) -> List[str]:
    """
    Download (if needed) and parse a Nanaimo bylaw into coarse paragraphs.
    """
    cfg = _get_bylaw_config(bylaw_id)
    pdf_path = _download_bylaw_pdf(cfg)
    text = _extract_text_from_pdf(pdf_path)
    return _split_into_paragraphs(text)


def naive_search_bylaw(question: str, max_results: int = 8) -> BylawAnswer:
    """
    Extremely simple keyword-based search over all core Nanaimo building-related bylaws.

    This is meant as a lightweight starting point; you can later replace it with
    an OpenSearch-backed or embedding-based retrieval layer.
    """
    q = question.lower()

    scored: List[tuple[int, str, str]] = []
    for cfg in BYLAWS:
        bylaw_id = cfg["id"]
        paragraphs = _load_bylaw_paragraphs(bylaw_id)
        for para in paragraphs:
            text_lower = para.lower()
            score = 0
            for term in q.split():
                if term and term in text_lower:
                    score += 1
            if score > 0:
                scored.append((score, bylaw_id, para))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:max_results]

    excerpts: List[BylawExcerpt] = []
    for _, bylaw_id, para in top:
        cfg = _get_bylaw_config(bylaw_id)
        excerpts.append(
            BylawExcerpt(
                source=cfg["name"],
                heading=None,
                snippet=para[:800] + ("..." if len(para) > 800 else ""),
            )
        )

    if not excerpts:
        summary = (
            "No obviously relevant passages were found in the selected Nanaimo bylaws "
            "for this question. You may need to consult the full bylaws."
        )
    else:
        summary = (
            "Here are a few sections from key Nanaimo bylaws (zoning, building, parking, "
            "fees, etc.) that mention terms from your question. Review them carefully "
            "and cross‑check with the official bylaw PDFs before relying on them."
        )

    return BylawAnswer(summary=summary, excerpts=excerpts)

