import unittest
import asyncio
import inspect
import sys
import types

# Mock heavy external dependencies before importing the pipeline
_mock_modules = [
    "moviepy",
    "moviepy.editor",
    "PIL",
    "PIL.Image",
    "agents",
    "interfaces",
    "interfaces.character",
    "interfaces.scene",
    "tools",
    "tools.render_backend",
    "utils",
    "utils.provider_presets",
    "langchain",
    "langchain.chat_models",
    "yaml",
]

for _mod_name in _mock_modules:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = types.ModuleType(_mod_name)

# Provide specific attribute stubs
sys.modules["moviepy"].VideoFileClip = object
sys.modules["moviepy"].concatenate_videoclips = lambda x: None
sys.modules["PIL.Image"] = types.ModuleType("PIL.Image")
sys.modules["PIL.Image"].Image = object

# Mock interfaces submodules
for _sub in ["character", "scene", "camera", "frame", "image_output", "video_output", "shot_description", "event"]:
    _full = f"interfaces.{_sub}"
    if _full not in sys.modules:
        sys.modules[_full] = types.ModuleType(_full)

class _CharacterInScene:
    def __init__(self, **kwargs):
        pass
    @classmethod
    def model_validate(cls, x):
        return cls()
    def model_dump(self):
        return {}

sys.modules["interfaces"].CharacterInScene = _CharacterInScene
sys.modules["interfaces.character"].CharacterInScene = _CharacterInScene

# Mock other interfaces classes on both main module and submodules
_interfaces_map = {
    "ShotDescription": "shot_description",
    "ShotBriefDescription": "shot_description",
    "Camera": "camera",
    "ImageOutput": "image_output",
    "VideoOutput": "video_output",
    "Frame": "frame",
    "Event": "event",
    "Scene": "scene",
    "CharacterInEvent": "character",
    "CharacterInNovel": "character",
}
for _cls_name, _sub in _interfaces_map.items():
    _cls = type(_cls_name, (), {})
    setattr(sys.modules["interfaces"], _cls_name, _cls)
    setattr(sys.modules[f"interfaces.{_sub}"], _cls_name, _cls)

# Mock agents submodules
for _sub in ["screenwriter", "storyboard_artist", "camera_image_generator", "character_extractor", "character_portraits_generator", "reference_image_selector"]:
    _full = f"agents.{_sub}"
    if _full not in sys.modules:
        sys.modules[_full] = types.ModuleType(_full)

# Provide minimal stubs for classes/functions used in __init__
class _DummyAgent:
    def __init__(self, **kwargs):
        pass

for _cls in [
    "CharacterExtractor",
    "CharacterPortraitsGenerator",
    "StoryboardArtist",
    "CameraImageGenerator",
    "ReferenceImageSelector",
    "Screenwriter",
]:
    setattr(sys.modules["agents"], _cls, _DummyAgent)
    # Also set on submodule
    _sub_map = {
        "CharacterExtractor": "character_extractor",
        "CharacterPortraitsGenerator": "character_portraits_generator",
        "StoryboardArtist": "storyboard_artist",
        "CameraImageGenerator": "camera_image_generator",
        "ReferenceImageSelector": "reference_image_selector",
        "Screenwriter": "screenwriter",
    }
    setattr(sys.modules[f"agents.{_sub_map[_cls]}"], _cls, _DummyAgent)

sys.modules["langchain.chat_models"].init_chat_model = lambda **kw: object()
sys.modules["tools.render_backend"].RenderBackend = type("RenderBackend", (), {})
sys.modules["utils.provider_presets"].resolve_chat_model_config = lambda x: {}
sys.modules["yaml"].safe_load = lambda x: {}

from pipelines.script2video_pipeline import Script2VideoPipeline


class TestScript2VideoPipelineEventState(unittest.TestCase):

    def test_event_dicts_are_instance_level_independent_objects(self):
        """Test 1: Three event dicts must be instance-level independent objects."""
        pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a",
        )
        pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b",
        )

        self.assertIsNot(
            pipeline_a.character_portrait_events,
            pipeline_b.character_portrait_events,
            "character_portrait_events should be independent between instances",
        )
        self.assertIsNot(
            pipeline_a.shot_desc_events,
            pipeline_b.shot_desc_events,
            "shot_desc_events should be independent between instances",
        )
        self.assertIsNot(
            pipeline_a.frame_events,
            pipeline_b.frame_events,
            "frame_events should be independent between instances",
        )

    def test_write_frame_events_does_not_pollute_other_instances(self):
        """Test 2: Writing to frame_events must not pollute other instances."""
        pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a",
        )
        pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b",
        )

        pipeline_a.frame_events[0] = {"first_frame": asyncio.Event()}

        self.assertIn(0, pipeline_a.frame_events)
        self.assertNotIn(0, pipeline_b.frame_events)
        self.assertEqual(pipeline_b.frame_events, {})

    def test_write_shot_desc_and_character_portrait_events_does_not_pollute_other_instances(self):
        """Test 3: Writing to shot_desc_events and character_portrait_events must not pollute other instances."""
        pipeline_a = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_a",
        )
        pipeline_b = Script2VideoPipeline(
            chat_model=object(),
            image_generator=object(),
            video_generator=object(),
            working_dir=".test/pipeline_b",
        )

        pipeline_a.shot_desc_events[3] = asyncio.Event()
        pipeline_a.character_portrait_events[7] = asyncio.Event()

        self.assertIn(3, pipeline_a.shot_desc_events)
        self.assertNotIn(3, pipeline_b.shot_desc_events)
        self.assertIn(7, pipeline_a.character_portrait_events)
        self.assertNotIn(7, pipeline_b.character_portrait_events)

    def test_no_class_level_shared_dict_in_source(self):
        """Test 4: Source code must not retain class-level shared dict definitions."""
        source = inspect.getsource(Script2VideoPipeline)

        # Check for class-level definitions: lines that start with the name (not self.)
        lines = source.split('\n')
        for line in lines:
            stripped = line.strip()
            self.assertFalse(
                stripped.startswith("character_portrait_events = {}"),
                "Source must not contain class-level character_portrait_events = {}",
            )
            self.assertFalse(
                stripped.startswith("shot_desc_events = {}"),
                "Source must not contain class-level shot_desc_events = {}",
            )
            self.assertFalse(
                stripped.startswith("frame_events = {}"),
                "Source must not contain class-level frame_events = {}",
            )

        init_source = inspect.getsource(Script2VideoPipeline.__init__)
        self.assertIn(
            "self.character_portrait_events",
            init_source,
            "__init__ must contain self.character_portrait_events",
        )
        self.assertIn(
            "self.shot_desc_events",
            init_source,
            "__init__ must contain self.shot_desc_events",
        )
        self.assertIn(
            "self.frame_events",
            init_source,
            "__init__ must contain self.frame_events",
        )


if __name__ == "__main__":
    unittest.main()
