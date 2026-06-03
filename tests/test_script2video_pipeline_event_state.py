import unittest
import asyncio
import inspect
from pipelines.script2video_pipeline import Script2VideoPipeline


class TestScript2VideoPipelineEventState(unittest.TestCase):

    def setUp(self):
        self.pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a",
        )
        self.pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b",
        )

    def test_event_dicts_are_instance_level_independent(self):
        self.assertIsNot(
            self.pipeline_a.character_portrait_events,
            self.pipeline_b.character_portrait_events,
        )
        self.assertIsNot(
            self.pipeline_a.shot_desc_events,
            self.pipeline_b.shot_desc_events,
        )
        self.assertIsNot(
            self.pipeline_a.frame_events,
            self.pipeline_b.frame_events,
        )

    def test_write_frame_events_does_not_pollute_other_instance(self):
        self.pipeline_a.frame_events[0] = {"first_frame": asyncio.Event()}

        self.assertIn(0, self.pipeline_a.frame_events)
        self.assertNotIn(0, self.pipeline_b.frame_events)
        self.assertEqual(self.pipeline_b.frame_events, {})

    def test_write_shot_desc_and_character_portrait_events_do_not_pollute(self):
        self.pipeline_a.shot_desc_events[3] = asyncio.Event()
        self.pipeline_a.character_portrait_events[7] = asyncio.Event()

        self.assertIn(3, self.pipeline_a.shot_desc_events)
        self.assertNotIn(3, self.pipeline_b.shot_desc_events)

        self.assertIn(7, self.pipeline_a.character_portrait_events)
        self.assertNotIn(7, self.pipeline_b.character_portrait_events)

    def test_source_code_has_no_class_level_shared_dict_definitions(self):
        self.assertNotIn(
            "character_portrait_events", Script2VideoPipeline.__dict__
        )
        self.assertNotIn(
            "shot_desc_events", Script2VideoPipeline.__dict__
        )
        self.assertNotIn(
            "frame_events", Script2VideoPipeline.__dict__
        )

        init_source = inspect.getsource(Script2VideoPipeline.__init__)
        self.assertIn("self.character_portrait_events", init_source)
        self.assertIn("self.shot_desc_events", init_source)
        self.assertIn("self.frame_events", init_source)


if __name__ == "__main__":
    unittest.main()