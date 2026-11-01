import os
import unittest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@127.0.0.1:5432/change_app_test",
)

from app.ai.intent_router import is_action_request, mentions_open_task, plan_sources  # noqa: E402

TITLES = ["Finish portfolio website", "Pay electricity bill"]


def plan(message):
    return plan_sources(message, task_titles=TITLES)


class ComposablePlanTests(unittest.TestCase):
    def test_current_tasks_question_loads_tasks(self):
        p = plan("What tasks am I currently working on?")
        self.assertTrue(p.need_tasks)
        self.assertFalse(p.need_memory)

    def test_postponing_loads_tasks_events_behavior_and_memory(self):
        p = plan("What have I been postponing recently?")
        self.assertTrue(all([p.need_tasks, p.need_events, p.need_behavior, p.need_memory]))

    def test_recall_loads_memory_without_tasks(self):
        p = plan("Do you remember what I told you about my career goals?")
        self.assertTrue(p.need_memory)
        self.assertFalse(p.need_tasks)

    def test_check_in_struggle_combines_memory_and_task_history(self):
        p = plan("Based on my recent check-ins, why might I be struggling with this task?")
        self.assertTrue(p.need_memory)
        self.assertEqual(p.memory_source_types, ("check_in", "brain_dump"))
        self.assertTrue(p.need_tasks and p.need_events and p.need_behavior)

    def test_naming_an_open_task_pulls_its_history(self):
        p = plan("why am I stuck on my portfolio?")
        self.assertTrue(p.need_tasks and p.need_events and p.need_behavior)

    def test_pure_mood_question_does_not_load_task_history(self):
        p = plan("how have I been feeling lately?")
        self.assertTrue(p.need_memory)
        self.assertFalse(p.need_events or p.need_behavior)

    def test_chitchat_loads_nothing(self):
        for message in ("hi", "Good morning", "Thanks, that helps"):
            p = plan(message)
            self.assertFalse(
                any([p.need_tasks, p.need_events, p.need_behavior, p.need_memory]), message
            )

    def test_out_of_scope_loads_nothing_and_is_not_an_action(self):
        p = plan("write me a python script")
        self.assertEqual(p.intent, "out_of_scope")
        self.assertFalse(any([p.need_tasks, p.need_memory, p.action_intent]))

    def test_sources_are_independent(self):
        # Memory cue + task cue in the same message select both, not one winner.
        p = plan("Remind me to send the portfolio, like I mentioned last week")
        self.assertTrue(p.need_memory and p.need_tasks and p.action_intent)


class ActionIntentTests(unittest.TestCase):
    def test_action_requests(self):
        for message in (
            "Add a task to call mum tomorrow",
            "remind me to pay rent",
            "please move my dentist task to Friday",
            "Can you cancel the gym task?",
        ):
            self.assertTrue(is_action_request(message), message)

    def test_non_actions(self):
        for message in (
            "What should I do today?",
            "I moved house last year",
            "How's my week looking?",
            "Thanks!",
        ):
            self.assertFalse(is_action_request(message), message)


class TitleMatchTests(unittest.TestCase):
    def test_matching(self):
        self.assertTrue(mentions_open_task("how is the portfolio going", TITLES))
        self.assertTrue(mentions_open_task("pay electricity", TITLES))
        self.assertFalse(mentions_open_task("what is the weather", TITLES))
        self.assertFalse(mentions_open_task("hi", []))


if __name__ == "__main__":
    unittest.main()


class FollowUpTests(unittest.TestCase):
    def test_short_follow_up_inherits_previous_sources(self):
        p = plan_sources(
            "and the week before?",
            previous_question="What did I write about my portfolio last week?",
            task_titles=TITLES,
        )
        self.assertTrue(p.need_memory)

    def test_follow_up_never_inherits_an_action(self):
        p = plan_sources("and tomorrow?", previous_question="Add a task to call mum", task_titles=TITLES)
        self.assertFalse(p.action_intent)

    def test_unrelated_long_message_does_not_inherit(self):
        p = plan_sources(
            "Tell me something encouraging about how my day is going so far",
            previous_question="What did I write about my portfolio last week?",
        )
        self.assertFalse(p.need_memory)

    def test_out_of_scope_previous_turn_is_not_inherited(self):
        p = plan_sources("and then?", previous_question="write me a python script")
        self.assertFalse(p.need_memory or p.need_tasks)
