import unittest

from app.memory.chunking import chunk_text


class ChunkingTests(unittest.TestCase):
    def test_empty_and_whitespace(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   \n "), [])

    def test_short_text_is_one_chunk(self):
        self.assertEqual(chunk_text("Call mum tomorrow."), ["Call mum tomorrow."])

    def test_long_text_splits_and_respects_limit(self):
        source = " ".join(f"This is sentence number {i}." for i in range(80))
        chunks = chunk_text(source, max_chars=300, overlap_chars=60)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 300 for chunk in chunks))

    def test_no_sentence_text_is_lost(self):
        source = " ".join(f"Sentence {i} ends here." for i in range(60))
        indexed_text = " ".join(chunk_text(source, max_chars=250, overlap_chars=50))
        for index in range(60):
            self.assertIn(f"Sentence {index} ends here.", indexed_text)

    def test_long_unpunctuated_text_is_hard_split(self):
        chunks = chunk_text("a" * 2500, max_chars=900, overlap_chars=0)
        self.assertTrue(all(len(chunk) <= 900 for chunk in chunks))
        self.assertEqual(sum(map(len, chunks)), 2500)

    def test_rejects_invalid_chunk_sizes(self):
        with self.assertRaises(ValueError):
            chunk_text("some text", max_chars=0)
        with self.assertRaises(ValueError):
            chunk_text("some text", max_chars=10, overlap_chars=10)


if __name__ == "__main__":
    unittest.main()
