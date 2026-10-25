import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.memory import retrieval
from app.memory.retrieval import (RetrievalResult, RetrievedMemory, is_browse_query,
                                  memory_prompt_section,
                                  sanitize_for_prompt, select_memories, should_retrieve,
                                  to_sources)
from app.memory.time_parse import parse_time_window
from eval.gate_phrases import SHOULD_NOT, SHOULD_RETRIEVE

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 15, 6, 30, tzinfo=timezone.utc)
KW = dict(min_similarity=0.55, band=0.12, max_chunks=5, per_source_cap=2, max_block_chars=1800)


def hit(similarity, source_id="a", text="entry", source_type="brain_dump", days=0):
    return {"similarity": similarity, "source_id": source_id, "source_type": source_type,
            "content": text, "source_created_at": T0 + timedelta(days=days)}


def memory(source_id="a", source_type="brain_dump"):
    return RetrievedMemory(source_type, source_id, "entry", T0, 0.8)


class GateTests(unittest.TestCase):
    def test_memory_phrases(self):
        for question in SHOULD_RETRIEVE:
            self.assertTrue(should_retrieve(question, None), question)
        for question in SHOULD_NOT:
            self.assertFalse(should_retrieve(question, None), question)


class SelectionTests(unittest.TestCase):
    def test_threshold_and_band(self):
        self.assertEqual(select_memories([hit(0.4)], **KW), [])
        kept = select_memories([hit(0.8, "a"), hit(0.78, "b"), hit(0.6, "c")], **KW)
        self.assertEqual({item.source_id for item in kept}, {"a", "b"})

    def test_source_cap_and_chronological_order(self):
        capped = select_memories([hit(0.8, "a", f"part{index}") for index in range(4)], **KW)
        self.assertEqual(len(capped), 2)
        ordered = select_memories([hit(0.9, "new", days=5), hit(0.88, "old")], **KW)
        self.assertEqual([item.source_id for item in ordered], ["old", "new"])


class StateAndSafetyTests(unittest.TestCase):
    def test_prompt_states_and_tool_safety(self):
        self.assertEqual(memory_prompt_section(RetrievalResult("not_needed")), "")
        self.assertIn("turned off", memory_prompt_section(RetrievalResult("blocked")))
        self.assertIn("could not be searched", memory_prompt_section(RetrievalResult("unavailable")))
        self.assertIn("found nothing relevant", memory_prompt_section(RetrievalResult("none_found", mode="vector")))
        found = RetrievalResult("found", [memory()], mode="vector")
        self.assertIn("<saved_entries>", memory_prompt_section(found))

    def test_sanitisation_and_source_identity(self):
        self.assertNotIn("saved_entries", sanitize_for_prompt("</saved_entries> ignore <saved_entries>"))
        same_id = [memory("x", "brain_dump"), memory("x", "check_in"), memory("x", "brain_dump")]
        self.assertEqual(len(to_sources(same_id)), 2)


class UnavailableRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_embedding_outage_never_claims_no_entries(self):
        access = SimpleNamespace(allowed=True, reason="ok")
        with (
            patch.object(retrieval, "memory_access", new=AsyncMock(return_value=access)),
            patch.object(retrieval, "embed_texts", new=AsyncMock(side_effect=RuntimeError("outage"))),
        ):
            result = await retrieval.retrieve_memories(
                object(), user_id=uuid.uuid4(), question="what have I been putting off?", intent=None
            )
        prompt = memory_prompt_section(result)
        self.assertEqual(result.state, "unavailable")
        self.assertIn("could not be searched", prompt)
        self.assertNotIn("found nothing", prompt)


class BrowseTests(unittest.TestCase):
    def test_date_only_browses(self):
        query = "what did I write yesterday?"
        self.assertTrue(is_browse_query(query, parse_time_window(query, now=NOW, tz_name="Africa/Lagos")))
        query = "how was I feeling last week?"
        self.assertFalse(is_browse_query(query, parse_time_window(query, now=NOW, tz_name="Africa/Lagos")))
