import { FormEvent, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type ParcelRaw = {
  Address?: string;
  ZoneCode?: string;
  ZoneDescription?: string;
  FOLIO?: string;
  PropertyReport?: string;
  Shape_Area?: number;
  [key: string]: unknown;
};

type ParcelAttributes = {
  OBJECTID?: number | null;
  civic_address?: string | null;
  folio?: string | null;
  zoning?: string | null;
  lot_area_sq_m?: number | null;
  raw: ParcelRaw;
};

type ParcelGeometry = {
  wkid?: number | null;
  x?: number | null;
  y?: number | null;
};

type ParcelInfo = {
  attributes: ParcelAttributes;
  geometry?: ParcelGeometry | null;
  arcgis_feature_id?: number | null;
};

type BylawExcerpt = {
  source: string;
  heading?: string | null;
  snippet: string;
};

type BylawAnswer = {
  summary: string;
  excerpts: BylawExcerpt[];
};

type AnalysisResponse = {
  address: string;
  parcel?: ParcelInfo | null;
  bylaw_answer?: BylawAnswer | null;
  llm_answer?: string | null;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.toString().replace(/\/$/, "") ||
  "http://localhost:8000";

function App() {
  const [address, setAddress] = useState("");
  const [question, setQuestion] = useState(
    "What kinds of small-scale housing or gentle density might be feasible on this property, and what should I watch out for?",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const hasBylaws =
    result?.bylaw_answer && result.bylaw_answer.excerpts.length > 0;

  const parcel = result?.parcel;
  const attrs = parcel?.attributes;
  const zoningCode =
    attrs?.raw.ZoneCode ?? attrs?.zoning ?? "(not available from GIS)";
  const zoningDesc = attrs?.raw.ZoneDescription;

  const lotAreaSqM = useMemo(() => {
    if (!attrs) return null;
    if (attrs.lot_area_sq_m) return attrs.lot_area_sq_m;
    if (typeof attrs.raw.Shape_Area === "number") return attrs.raw.Shape_Area;
    return null;
  }, [attrs]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    const trimmedAddress = address.trim();
    if (!trimmedAddress) {
      setError("Please enter an address in Nanaimo.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          address: trimmedAddress,
          question: question.trim() || null,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(
          `API error (${response.status}): ${
            detail || response.statusText || "Unknown error"
          }`,
        );
      }

      const json: AnalysisResponse = await response.json();
      setResult(json);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Unexpected error from API.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      <div className="app-shell">
        <header className="app-header">
          <div className="app-title">Nanaimo Property Insights</div>
          <div className="app-subtitle">
            Type a Nanaimo address and a question. The app looks up basic parcel
            details and suggests development ideas using local bylaws.
          </div>
        </header>

        <div className="layout">
          <section className="card">
            <div className="card-header">
              <div className="card-title">Search</div>
              <span className="badge">Local API: /analyze</span>
            </div>

            <form className="field-group" onSubmit={handleSubmit}>
              <div>
                <label className="field-label" htmlFor="address">
                  Address in Nanaimo, BC
                </label>
                <input
                  id="address"
                  className="input"
                  placeholder="e.g. 5709 Malibu Terrace"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  autoComplete="street-address"
                  required
                />
              </div>

              <div>
                <label className="field-label" htmlFor="question">
                  What do you want to know?
                </label>
                <textarea
                  id="question"
                  className="textarea"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                />
                <div className="helper-text">
                  For example: “Can I build a duplex or small multi-unit
                  building here and what issues should I consider?”
                </div>
              </div>

              <div className="actions">
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => {
                    setAddress("");
                    setQuestion("");
                    setResult(null);
                    setError(null);
                  }}
                >
                  Clear
                </button>
                <button
                  type="submit"
                  className="button button-primary"
                  disabled={loading}
                >
                  {loading ? "Analyzing…" : "Analyze property"}
                </button>
              </div>

              <div className="status-row">
                <span>
                  API base: <code>{API_BASE_URL}</code>
                </span>
                {error ? (
                  <span className="status-pill status-pill-error">
                    Error from API
                  </span>
                ) : result ? (
                  <span className="status-pill status-pill-ok">Ready</span>
                ) : null}
              </div>
              {error && <div className="error-text">{error}</div>}
            </form>
          </section>

          <section className="card">
            <div className="card-header">
              <div className="card-title">AI answer</div>
              <span className="badge">
                {result?.parcel?.attributes?.raw.ZoneCode || "No zoning yet"}
              </span>
            </div>
            {result?.llm_answer ? (
              <article className="answer-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.llm_answer}
                </ReactMarkdown>
              </article>
            ) : (
              <div className="helper-text">
                Run an analysis to see a planning-oriented summary and potential
                development ideas for your property. LLM support must be
                configured on the backend.
              </div>
            )}
          </section>
        </div>

        {result && (
          <div className="layout" style={{ marginTop: "1.2rem" }}>
            <section className="card">
              <div className="card-header">
                <div className="card-title">Parcel details</div>
                <span className="badge">From Nanaimo GIS</span>
              </div>
              {parcel ? (
                <>
                  <div className="meta-grid">
                    <div>
                      <div className="meta-label">Address</div>
                      <div className="meta-value">
                        {attrs?.civic_address || attrs?.raw.Address || "—"}
                      </div>
                    </div>
                    <div>
                      <div className="meta-label">Zone</div>
                      <div className="meta-value">
                        {zoningCode}
                        {zoningDesc ? ` – ${zoningDesc}` : ""}
                      </div>
                    </div>
                    <div>
                      <div className="meta-label">Folio</div>
                      <div className="meta-value">
                        {attrs?.folio || attrs?.raw.FOLIO || "—"}
                      </div>
                    </div>
                    <div>
                      <div className="meta-label">Lot area (approx.)</div>
                      <div className="meta-value">
                        {lotAreaSqM
                          ? `${lotAreaSqM.toFixed(0)} m²`
                          : "Not provided"}
                      </div>
                    </div>
                  </div>
                  <div className="pill-row">
                    <span className="pill">
                      OBJECTID: {attrs?.raw.OBJECTID ?? "?"}
                    </span>
                    <span className="pill">
                      PID: {attrs?.raw.PID ?? "not provided"}
                    </span>
                    <span className="pill">
                      Plan: {attrs?.raw.PLANNAME ?? "not provided"}
                    </span>
                  </div>
                  {attrs?.raw.PropertyReport && (
                    <div style={{ marginTop: "0.7rem" }}>
                      <a
                        href={attrs.raw.PropertyReport}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View official City property report ↗
                      </a>
                    </div>
                  )}
                </>
              ) : (
                <div className="helper-text">
                  No parcel was found for this address in the Nanaimo parcel
                  search service.
                </div>
              )}
            </section>

            <section className="card">
              <div className="card-header">
                <div className="card-title">Bylaw context</div>
                <span className="badge">
                  {hasBylaws ? "Snippets loaded" : "No matches yet"}
                </span>
              </div>
              {result?.bylaw_answer && hasBylaws ? (
                <>
                  <div className="helper-text" style={{ marginBottom: "0.4rem" }}>
                    {result.bylaw_answer.summary}
                  </div>
                  <div className="excerpts-list">
                    {result.bylaw_answer.excerpts.map((ex, idx) => (
                      <details
                        key={`${ex.source}-${idx}`}
                        className="excerpt-item"
                      >
                        <summary>{ex.source}</summary>
                        <div className="excerpt-snippet">{ex.snippet}</div>
                      </details>
                    ))}
                  </div>
                </>
              ) : (
                <div className="helper-text">
                  Ask a question and the backend will pull a few relevant
                  passages from zoning, building, parking and other bylaws to
                  support the AI answer.
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

