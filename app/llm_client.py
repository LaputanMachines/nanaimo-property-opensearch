import os
from typing import Optional

import requests
from fastapi import HTTPException, status

from .models import BylawAnswer, ParcelInfo


def _build_prompt(
    address: str,
    question: str,
    parcel: Optional[ParcelInfo],
    bylaw_answer: Optional[BylawAnswer],
) -> str:
    lines = []
    lines.append(
        "You are an assistant helping with high‑level land use and "
        "development questions in Nanaimo, BC, Canada."
    )
    lines.append(
        "You are not a lawyer or planner; clearly state that this is "
        "informational only and users must confirm with the City."
    )
    lines.append("")
    lines.append(f"Property address: {address}")
    if parcel is not None:
        attrs = parcel.attributes
        zone_code = attrs.raw.get("ZoneCode") or attrs.zoning
        zone_desc = attrs.raw.get("ZoneDescription")
        lines.append(f"Zone code: {zone_code}")
        if zone_desc:
            lines.append(f"Zone description: {zone_desc}")
        if attrs.lot_area_sq_m:
            lines.append(f"Lot area (sq m): {attrs.lot_area_sq_m}")
        if attrs.folio:
            lines.append(f"Folio: {attrs.folio}")
    else:
        lines.append("No parcel record was found for this address.")

    lines.append("")
    lines.append(f"User question: {question}")

    if bylaw_answer and bylaw_answer.excerpts:
        lines.append("")
        lines.append(
            "Relevant excerpts from Nanaimo bylaws (zoning, building, parking, "
            "fees, etc.). Use these as supporting context but do NOT quote long "
            "passages verbatim; summarize what matters:"
        )
        for ex in bylaw_answer.excerpts:
            snippet = ex.snippet[:600]
            lines.append(f"- Source: {ex.source}")
            lines.append(f"  Snippet: {snippet}")

    lines.append("")
    lines.append(
        "Based on this information, answer the user's question in 2‑5 short "
        "paragraphs. Focus on:"
    )
    lines.append(
        "- What the zoning likely allows (e.g., single detached, duplex, townhouses, "
        "small multi‑unit, etc.) given the zone code."
    )
    lines.append(
        "- Any obvious constraints or additional bylaws that may be relevant "
        "(parking, subdivision, trees, building/servicing)."
    )
    lines.append(
        "- Concrete but high‑level development ideas that might be feasible on "
        "this lot, with appropriate caveats."
    )
    lines.append(
        "Always end with a short disclaimer reminding the user to confirm details "
        "with the City of Nanaimo and/or a qualified professional."
    )

    return "\n".join(lines)


def generate_llm_answer(
    address: str,
    question: str,
    parcel: Optional[ParcelInfo],
    bylaw_answer: Optional[BylawAnswer],
) -> Optional[str]:
    """
    Call an LLM provider to generate a natural-language answer.

    Priority:
    - If ANTHROPIC_API_KEY is set, call Anthropic Messages API.
    - Else if OPENAI_API_KEY is set, call OpenAI Chat Completions API.
    - Else return None so the API can still function without LLM support.
    """
    prompt = _build_prompt(address=address, question=question, parcel=parcel, bylaw_answer=bylaw_answer)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        url = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")

        try:
            resp = requests.post(
                url,
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 800,
                    "temperature": 0.4,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                },
                timeout=30,
            )
            if not resp.ok:
                # Log full error body to the server console (tmux) for debugging.
                print("Anthropic error:", resp.status_code, resp.text)  # noqa: T201
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error calling Anthropic: {exc}",
            ) from exc

        data = resp.json()
        try:
            # content is a list of blocks; we assume first is text
            return (data["content"][0]["text"] or "").strip()
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unexpected response from Anthropic: {data}",
            ) from exc

    # Fallback: OpenAI, if configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        url = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")

        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful planning and development assistant for Nanaimo, BC.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                },
                timeout=30,
            )
            if not resp.ok:
                # Log full error body to the server console (tmux) for debugging.
                print("OpenAI error:", resp.status_code, resp.text)  # noqa: T201
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error calling OpenAI: {exc}",
            ) from exc

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unexpected response from OpenAI: {data}",
            ) from exc

    # No provider configured
    return None

