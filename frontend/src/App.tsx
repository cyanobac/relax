import { useState } from "react";
import { extractStress, type ExtractResult } from "./api";

function toCsv(result: ExtractResult): string {
  const rows = ["timestamp,zone"];
  for (const p of result.points) rows.push(`${p.timestamp},${p.zone}`);
  return rows.join("\n");
}

function downloadCsv(result: ExtractResult, date: string) {
  const blob = new Blob([toCsv(result)], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `stress_zones_${date}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function App() {
  const [file, setFile] = useState<File | null>(null);
  const [date, setDate] = useState("");
  const [includeImage, setIncludeImage] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractResult | null>(null);

  const canSubmit = file !== null && date !== "" && !loading;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !date) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await extractStress(file, date, includeImage));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <h1>Oura Stress Extractor</h1>
      <p className="subtitle">
        Drop an Oura "Daytime Stress" screenshot (640×1136) and pick its date.
      </p>

      <form onSubmit={onSubmit} className="card">
        <label className="field">
          <span>Screenshot</span>
          <input
            type="file"
            accept="image/png,image/jpeg"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label className="field">
          <span>Chart date</span>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={includeImage}
            onChange={(e) => setIncludeImage(e.target.checked)}
          />
          <span>Show annotated chart</span>
        </label>

        <button type="submit" disabled={!canSubmit}>
          {loading ? "Processing…" : "Extract"}
        </button>
      </form>

      {error && <div className="error">⚠️ {error}</div>}

      {result && (
        <section className="results">
          {result.warnings.length > 0 && (
            <ul className="warnings">
              {result.warnings.map((w, i) => (
                <li key={i}>⚠️ {w}</li>
              ))}
            </ul>
          )}

          <div className="results-header">
            <h2>{result.points.length} data points</h2>
            <button type="button" onClick={() => downloadCsv(result, date)}>
              Download CSV
            </button>
          </div>

          {result.annotated_png && (
            <img
              className="annotated"
              src={`data:image/png;base64,${result.annotated_png}`}
              alt="Annotated stress chart"
            />
          )}

          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Zone</th>
              </tr>
            </thead>
            <tbody>
              {result.points.map((p, i) => (
                <tr key={i}>
                  <td>{p.timestamp.replace("T", " ")}</td>
                  <td className={`zone zone-${p.zone}`}>{p.zone}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
