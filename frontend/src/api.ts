export type StressPoint = {
  timestamp: string;
  zone: string;
};

export type Gap = {
  after: string;
  before: string;
  gap_minutes: number;
  missing_points: number;
};

export type ExtractResult = {
  points: StressPoint[];
  gaps: Gap[];
  warnings: string[];
  meta: {
    reference_date: string;
    first_time: string;
    last_time: string;
    detected_dots: number;
    used_dots: number;
  };
  annotated_png?: string;
};

export async function extractStress(
  file: File,
  date: string,
  includeImage: boolean
): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("date", date);
  form.append("include_image", String(includeImage));

  const res = await fetch("/api/extract", { method: "POST", body: form });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}
