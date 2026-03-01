import os
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException, status

from .models import ParcelAttributes, ParcelGeometry, ParcelInfo


class ArcgisParcelClient:
    """
    Minimal client for the City of Nanaimo ArcGIS ParcelSearch MapServer.

    The exact layer index and field names are configurable so you can tweak them
    after inspecting https://nanmap.nanaimo.ca/arcgis/rest/services/NanMap/ParcelSearch/MapServer
    in a browser.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        layer_index: Optional[int] = None,
        address_field: Optional[str] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv(
                "NANAIMO_ARCGIS_BASE_URL",
                "https://nanmap.nanaimo.ca/arcgis/rest/services/NanMap/ParcelSearch/MapServer",
            )
        )
        self.layer_index = layer_index or int(
            os.getenv("NANAIMO_ARCGIS_LAYER_INDEX", "0"),
        )
        # This should be set to the parcel address field name after you inspect the service.
        # For the current ParcelSearch layer, the field is named 'Address'.
        self.address_field = address_field or os.getenv(
            "NANAIMO_ARCGIS_ADDRESS_FIELD",
            "Address",
        )

    def _layer_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.layer_index}"

    def search_parcel_by_address(self, address: str) -> Optional[ParcelInfo]:
        """
        Naive address search using a LIKE query against the configured address field.
        """
        if not address.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Address must not be empty.",
            )

        query_url = f"{self._layer_url()}/query"
        # This WHERE clause is intentionally simple; you can refine it once you know the schema.
        safe_address = address.replace("'", "''")
        where = f"UPPER({self.address_field}) LIKE UPPER('%{safe_address}%')"

        params = {
            "f": "json",
            "where": where,
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": 1,
        }

        try:
            resp = requests.get(query_url, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error querying Nanaimo ArcGIS service: {exc}",
            ) from exc

        data: Dict[str, Any] = resp.json()

        if "error" in data:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"ArcGIS service error: {data['error'].get('message')}",
            )

        features = data.get("features") or []
        if not features:
            return None

        feature = features[0]
        attrs: Dict[str, Any] = feature.get("attributes") or {}
        geom: Dict[str, Any] = feature.get("geometry") or {}

        parcel_attrs = ParcelAttributes(
            civic_address=attrs.get(self.address_field),
            folio=str(attrs.get("FOLIO")) if attrs.get("FOLIO") is not None else None,
            zoning=attrs.get("ZONING"),
            lot_area_sq_m=attrs.get("AREA_SQM"),
            raw=attrs,
        )

        parcel_geom = None
        if geom:
            parcel_geom = ParcelGeometry(
                wkid=(geom.get("spatialReference") or {}).get("wkid"),
                x=geom.get("x"),
                y=geom.get("y"),
            )

        return ParcelInfo(
            attributes=parcel_attrs,
            geometry=parcel_geom,
            arcgis_feature_id=attrs.get("OBJECTID"),
        )

