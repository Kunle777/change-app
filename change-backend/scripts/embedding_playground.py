import asyncio

import numpy as np
from dotenv import load_dotenv

load_dotenv()

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


async def main() -> None:
    docs = np.array(await embed_texts(DOCS, task_type="RETRIEVAL_DOCUMENT"))
    queries = np.array(await embed_texts(QUERIES, task_type="RETRIEVAL_QUERY"))
    similarities = queries @ docs.T

    for query, row in zip(QUERIES, similarities):
        print(f"\nQUERY: {query}")
        for index in np.argsort(-row)[:3]:
            print(f"  {row[index]:.3f}  {DOCS[index]}")

    print("\n'did not finish' vs 'finished':", round(float(docs[6] @ docs[7]), 3))


if __name__ == "__main__":
    asyncio.run(main())
