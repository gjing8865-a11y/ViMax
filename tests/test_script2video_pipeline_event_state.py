import unittest
import asyncio
import inspect
import os
from pipelines.script2video_pipeline import Script2VideoPipeline


class TestScript2VideoPipelineEventState(unittest.TestCase):

    def test_events_are_instance_level_objects(self):
        # 测试 1：三个事件字典必须是实例级独立对象
        pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a"
        )
        pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b"
        )
        
        self.assertIsNot(pipeline_a.character_portrait_events, pipeline_b.character_portrait_events)
        self.assertIsNot(pipeline_a.shot_desc_events, pipeline_b.shot_desc_events)
        self.assertIsNot(pipeline_a.frame_events, pipeline_b.frame_events)

    def test_writing_frame_events_not_polluting_other_instances(self):
        # 测试 2：写入 frame_events 不得污染其他实例
        pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a"
        )
        pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b"
        )
        
        pipeline_a.frame_events[0] = {"first_frame": asyncio.Event()}
        
        self.assertIn(0, pipeline_a.frame_events)
        self.assertNotIn(0, pipeline_b.frame_events)
        self.assertEqual(pipeline_b.frame_events, {})

    def test_writing_shot_desc_and_character_portrait_events_not_polluting_other_instances(self):
        # 测试 3：写入 shot_desc_events 和 character_portrait_events 不得污染其他实例
        pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a"
        )
        pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b"
        )
        
        pipeline_a.shot_desc_events[3] = asyncio.Event()
        pipeline_a.character_portrait_events[7] = asyncio.Event()
        
        self.assertIn(3, pipeline_a.shot_desc_events)
        self.assertNotIn(3, pipeline_b.shot_desc_events)
        self.assertIn(7, pipeline_a.character_portrait_events)
        self.assertNotIn(7, pipeline_b.character_portrait_events)

    def test_no_class_level_shared_dictionaries_in_source_code(self):
        # 测试 4：源码中不得再保留类级共享字典定义
        source_code = inspect.getsource(Script2VideoPipeline)
        
        self.assertNotIn("character_portrait_events = {}", source_code)
        self.assertNotIn("shot_desc_events = {}", source_code)
        self.assertNotIn("frame_events = {}", source_code)
        
        init_source_code = inspect.getsource(Script2VideoPipeline.__init__)
        self.assertIn("self.character_portrait_events", init_source_code)
        self.assertIn("self.shot_desc_events", init_source_code)
        self.assertIn("self.frame_events", init_source_code)


if __name__ == "__main__":
    unittest.main()
