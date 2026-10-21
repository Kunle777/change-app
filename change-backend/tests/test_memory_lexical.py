import unittest

from app.memory.lexical import content_terms


class LexicalTests(unittest.TestCase):
    def test_question_words_are_dropped(self):
        self.assertEqual(content_terms("What did I write about Kilnart?"), ["kilnart"])

    def test_date_only_questions_have_no_content(self):
        self.assertEqual(content_terms("What did I write yesterday?"), [])
        self.assertEqual(content_terms("what was I up to last week?"), [])

    def test_entities_survive_alongside_dates(self):
        self.assertEqual(content_terms("anything about the AWS exam this week?"), ["aws", "exam"])
