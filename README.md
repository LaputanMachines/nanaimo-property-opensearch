## nanaimo-property-opensearch

AI tool to answer property-related questions and to suggest development opportunities on parcels of land in Nanaimo, BC.

### What this API does

- **Property lookup**: Given a Nanaimo address, it queries the City of Nanaimo's ArcGIS `ParcelSearch` service to fetch basic parcel information (address, folio, zoning, approximate lot area, and raw attributes).
- **Bylaw context**: Given an optional natural-language question, it downloads and parses **Zoning Bylaw No. 4500** and runs a simple keyword search to return potentially relevant passages.
- **Integration surface**: Exposes everything via a small **FastAPI** service so it can be integrated into other tools or frontends.

### Running the API locally

- **1. Create and activate a virtualenv**

```bash
cd nanaimo-property-opensearch
python -m venv .venv
source .venv/bin/activate
```

- **2. Install dependencies**

```bash
pip install -r requirements.txt
```

- **3. (Optional) Configure environment**

Create a `.env` file in the project root if you want to override defaults and/or enable LLM answers:

```bash
NANAIMO_ARCGIS_BASE_URL=https://nanmap.nanaimo.ca/arcgis/rest/services/NanMap/ParcelSearch/MapServer
NANAIMO_ARCGIS_LAYER_INDEX=0
NANAIMO_ARCGIS_ADDRESS_FIELD=Address
NANAIMO_ZONING_BYLAW_URL=https://www.nanaimo.ca/bylaws/ViewBylaw/4500.pdf
NANAIMO_BYLAW_DATA_DIR=./data

# Optional: enable LLM-generated answer text (Anthropic preferred)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Or, fallback to OpenAI if you prefer
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4.1-mini
```

- **4. Start the API**

```bash
uvicorn app.main:app --reload
```

FastAPI's interactive docs will then be available at:

- **OpenAPI/Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Optional: React UI frontend

There is a small React/Vite frontend under `frontend/` that calls the `/analyze` API and presents:

- **Search form** for address + question
- **LLM answer** as the primary view
- **Parcel details** (zoning, folio, area, links)
- **Bylaw snippets** in collapsible sections for traceability

To run it (once you have Node/npm installed):

```bash
cd frontend
npm install
npm run dev
```

By default it assumes the API is at `http://localhost:8000`. You can override this with:

```bash
VITE_API_BASE_URL=https://your-api-host
```

and the backend CORS origin with:

```bash
FRONTEND_ORIGIN=http://localhost:5173
```

### Deploying on Railway

This repo is configured for a simple **backend deployment** on Railway using Nixpacks and `uvicorn`:

- `railway.json` specifies:

```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

To deploy:

- Push this repo to GitHub.
- In Railway, create a new project and select this repo.
- Railway will detect Python + `requirements.txt` and use the `railway.json` `startCommand`.
- In the Railway service, configure environment variables (match your local `.env`, especially the ArcGIS and bylaw URLs and any `ANTHROPIC_` / `OPENAI_` keys).
- In the service Networking settings, click **Generate Domain** to get a public URL for the FastAPI backend.

You can then point the React frontend (deployed separately, e.g. another Railway Node service or any static host) at that URL via `VITE_API_BASE_URL`.

### Example request

`POST /analyze`

```json
{
  "address": "123 Main St",
  "question": "Can I build a duplex here and what are the setback requirements?"
}
```

### Notes and next steps

- **Parcel schema tuning**: After inspecting the ArcGIS service in a browser, you should refine the configured `address_field` and any other fields you care about (lot size, OCP designation, etc.).
- **Smarter bylaw reasoning**: The current bylaw integration is a naive keyword search over the PDF text. It is intentionally simple so you can later plug in OpenSearch or an embedding-based retriever plus an LLM for richer answers and development suggestions.
