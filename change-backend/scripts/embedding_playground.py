import asyncio
import html
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.memory.embedding import embed_texts  # noqa: E402


DOCS = [
    "I keep putting off my portfolio website because I don't know where to start",
    "Finished the AI wrapper and submitted it ahead of the deadline",
    "Feeling exhausted and low today, couldn't focus on anything",
    "Need to buy milk and call mum before Friday",
    "Procrastinating on the website again, starting feels overwhelming",
    "Had a great workout this morning and felt energised",
    "I did not finish my report today",
    "I finished my report today",
]
QUERIES = [
    "what am I avoiding?",
    "when was I in a bad mood?",
    "errands I need to run",
    "did I complete my report?",
]
OUTPUT_PATH = Path(__file__).with_name("embedding_playground.html")


def write_plot(documents: np.ndarray, queries: np.ndarray) -> None:
    vectors = np.vstack((documents, queries))
    centered = vectors - vectors.mean(axis=0)
    _, singular_values, components = np.linalg.svd(centered, full_matrices=False)
    points = centered @ components[:2].T

    width, height = 1000, 680
    left, right, top, bottom = 90, 40, 55, 85
    plot_width = width - left - right
    plot_height = height - top - bottom
    x_min, y_min = points.min(axis=0)
    x_range, y_range = np.ptp(points, axis=0)
    x_range = x_range or 1.0
    y_range = y_range or 1.0

    def project(point: np.ndarray) -> tuple[float, float]:
        x = left + (point[0] - x_min) / x_range * plot_width
        y = top + (1 - (point[1] - y_min) / y_range) * plot_height
        return x, y

    variance = singular_values**2
    variance_percent = variance / variance.sum() * 100
    markers = []
    labels = []

    for index, text in enumerate(DOCS + QUERIES):
        x, y = project(points[index])
        is_query = index >= len(DOCS)
        color = "#dc5a45" if is_query else "#2767b1"
        marker = (
            f'<path d="M {x - 7:.1f} {y - 7:.1f} l 14 14 m 0 -14 l -14 14" '
            f'stroke="{color}" stroke-width="3" />'
            if is_query
            else f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" />'
        )
        markers.append(f'<g>{marker}<title>{html.escape(text)}</title></g>')
        short_text = text if len(text) <= 36 else text[:33] + "..."
        labels.append(
            f'<text x="{x + 10:.1f}" y="{y - 8:.1f}">'
            f'{html.escape(short_text)}</text>'
        )

    svg = f"""<svg viewBox="0 0 {width} {height}" role="img"
        aria-label="PCA plot of document and query embeddings">
      <style>
        text {{ font: 12px system-ui, sans-serif; fill: #263238; }}
        .axis {{ stroke: #9aa5b1; stroke-width: 1; }}
        .grid {{ stroke: #e5e9ed; stroke-width: 1; }}
      </style>
      <line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" />
      <line class="axis" x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" />
      <line class="grid" x1="{left}" y1="{top + plot_height / 2:.1f}" x2="{width - right}" y2="{top + plot_height / 2:.1f}" />
      <line class="grid" x1="{left + plot_width / 2:.1f}" y1="{top}" x2="{left + plot_width / 2:.1f}" y2="{height - bottom}" />
      <text x="{left + plot_width / 2:.1f}" y="{height - 28}" text-anchor="middle">
        Principal component 1 ({variance_percent[0]:.1f}% of variance)
      </text>
      <text transform="translate(24 {top + plot_height / 2:.1f}) rotate(-90)" text-anchor="middle">
        Principal component 2 ({variance_percent[1]:.1f}% of variance)
      </text>
      {''.join(markers)}
      {''.join(labels)}
    </svg>"""

    OUTPUT_PATH.write_text(
        f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Embedding playground</title>
<style>
  body {{ margin: 2rem auto; padding: 0 1rem; max-width: 1100px;
         color: #263238; font: 16px system-ui, sans-serif; }}
  svg {{ width: 100%; height: auto; border: 1px solid #e5e9ed;
         border-radius: 8px; }}
  .legend {{ display: flex; gap: 1.5rem; margin: 1rem 0; }}
  .document {{ color: #2767b1; }} .query {{ color: #dc5a45; }}
  .note {{ color: #59636e; }}
</style>
<h1>Embedding playground</h1>
<p class="note">Each point is a 768-dimensional embedding projected to two dimensions
with PCA. Hover over a point to read its full text. Nearby points can be related,
but this projection is only an approximate view of similarity.</p>
<div class="legend"><span class="document">● Documents</span>
<span class="query">× Queries</span></div>
{svg}
</html>
""",
        encoding="utf-8",
    )
    print(f"\nInteractive plot saved to: {OUTPUT_PATH}")


async def main() -> None:
    docs = np.array(await embed_texts(DOCS, task_type="RETRIEVAL_DOCUMENT"))
    queries = np.array(await embed_texts(QUERIES, task_type="RETRIEVAL_QUERY"))
    similarities = queries @ docs.T

    for query, row in zip(QUERIES, similarities):
        print(f"\nQUERY: {query}")
        for index in np.argsort(-row)[:3]:
            print(f"  {row[index]:.3f}  {DOCS[index]}")

    print("\n'did not finish' vs 'finished':", round(float(docs[6] @ docs[7]), 3))
    write_plot(docs, queries)


if __name__ == "__main__":
    asyncio.run(main())
