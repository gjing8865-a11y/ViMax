import asyncio
import inspect
import importlib.machinery
import re
import shutil
import sys
import types
import unittest


_STUBBED_MODULE_NAMES = [
    "moviepy",
    "yaml",
    "langchain",
    "langchain.chat_models",
    "langchain.chat_models.base",
    "langchain_core",
    "langchain_core.prompts",
    "langchain_core.output_parsers",
    "langchain_core.messages",
    "scenedetect",
    "scenedetect.detectors",
    "google",
    "google.genai",
    "google.genai.types",
    "google.genai.errors",
    "aiohttp",
    "faiss",
    "langchain_community",
    "langchain_community.vectorstores",
    "langchain_community.vectorstores.FAISS",
]
_ORIGINAL_MODULES = {name: sys.modules.get(name) for name in _STUBBED_MODULE_NAMES}


def _ensure_module(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is not None:
        return module

    module = types.ModuleType(name)
    module.__spec__ = importlib.machinery.ModuleSpec(name, None)
    module.__path__ = []
    sys.modules[name] = module

    if "." in name:
        parent_name, child_name = name.rsplit(".", 1)
        parent_module = _ensure_module(parent_name)
        setattr(parent_module, child_name, module)

    return module


moviepy = _ensure_module("moviepy")
moviepy.VideoFileClip = object
moviepy.concatenate_videoclips = lambda clips: clips

def _parse_yaml_scalar(value: str):
    lowered = value.lower()
    if lowered == "null":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value



def _simple_yaml_safe_load(stream):
    content = stream.read() if hasattr(stream, "read") else stream
    root = {}
    stack = [(-1, root)]

    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        line = re.split(r"\s+#", raw_line, maxsplit=1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        key, _, value = line.strip().partition(":")
        value = value.strip()

        while indent <= stack[-1][0]:
            stack.pop()

        current = stack[-1][1]
        if value == "":
            current[key] = {}
            stack.append((indent, current[key]))
        else:
            current[key] = _parse_yaml_scalar(value)

    return root



yaml = _ensure_module("yaml")
yaml.safe_load = _simple_yaml_safe_load

_ensure_module("langchain")
langchain_chat_models = _ensure_module("langchain.chat_models")
langchain_chat_models.init_chat_model = lambda **kwargs: object()
langchain_chat_models_base = _ensure_module("langchain.chat_models.base")
langchain_chat_models_base.BaseChatModel = type("BaseChatModel", (), {})

_ensure_module("langchain_core")
langchain_core_prompts = _ensure_module("langchain_core.prompts")
langchain_core_prompts.ChatPromptTemplate = type("ChatPromptTemplate", (), {})
langchain_core_output_parsers = _ensure_module("langchain_core.output_parsers")
langchain_core_output_parsers.PydanticOutputParser = type(
    "PydanticOutputParser",
    (),
    {
        "__init__": lambda self, *args, **kwargs: None,
        "get_format_instructions": lambda self: "",
    },
)
langchain_core_messages = _ensure_module("langchain_core.messages")
langchain_core_messages.HumanMessage = type(
    "HumanMessage",
    (),
    {"__init__": lambda self, content=None: setattr(self, "content", content)},
)
langchain_core_messages.SystemMessage = type(
    "SystemMessage",
    (),
    {"__init__": lambda self, content=None: setattr(self, "content", content)},
)

scenedetect = _ensure_module("scenedetect")
scenedetect.open_video = lambda *args, **kwargs: None
scenedetect.SceneManager = type("SceneManager", (), {})
scenedetect.split_video_ffmpeg = lambda *args, **kwargs: None
scenedetect_detectors = _ensure_module("scenedetect.detectors")
scenedetect_detectors.ContentDetector = type("ContentDetector", (), {})

_ensure_module("google")
google_genai = _ensure_module("google.genai")
google_genai.Client = type("Client", (), {"__init__": lambda self, *args, **kwargs: None})
google_genai_types = _ensure_module("google.genai.types")
google_genai_types.Image = type(
    "Image",
    (),
    {"from_file": staticmethod(lambda location=None, **kwargs: location)},
)
google_genai_errors = _ensure_module("google.genai.errors")
google_genai_errors.ClientError = type("ClientError", (Exception,), {})

_ensure_module("aiohttp")
_ensure_module("faiss")
_ensure_module("langchain_community")
_ensure_module("langchain_community.vectorstores")
_ensure_module("langchain_community.vectorstores.FAISS")

from pipelines.script2video_pipeline import Script2VideoPipeline


class TestScript2VideoPipelineEventState(unittest.TestCase):
    def setUp(self):
        self.working_dirs = [".test/pipeline_a", ".test/pipeline_b"]
        for working_dir in self.working_dirs:
            shutil.rmtree(working_dir, ignore_errors=True)

    def tearDown(self):
        for working_dir in self.working_dirs:
            shutil.rmtree(working_dir, ignore_errors=True)

    def _create_pipelines(self):
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
        return pipeline_a, pipeline_b

    def test_event_dictionaries_are_instance_local_objects(self):
        pipeline_a, pipeline_b = self._create_pipelines()

        self.assertIsNot(
            pipeline_a.character_portrait_events,
            pipeline_b.character_portrait_events,
        )
        self.assertIsNot(
            pipeline_a.shot_desc_events,
            pipeline_b.shot_desc_events,
        )
        self.assertIsNot(
            pipeline_a.frame_events,
            pipeline_b.frame_events,
        )

    def test_writing_frame_events_does_not_pollute_other_instance(self):
        pipeline_a, pipeline_b = self._create_pipelines()

        pipeline_a.frame_events[0] = {"first_frame": asyncio.Event()}

        self.assertIn(0, pipeline_a.frame_events)
        self.assertNotIn(0, pipeline_b.frame_events)
        self.assertEqual({}, pipeline_b.frame_events)

    def test_writing_shot_and_character_events_does_not_pollute_other_instance(self):
        pipeline_a, pipeline_b = self._create_pipelines()

        pipeline_a.shot_desc_events[3] = asyncio.Event()
        pipeline_a.character_portrait_events[7] = asyncio.Event()

        self.assertIn(3, pipeline_a.shot_desc_events)
        self.assertNotIn(3, pipeline_b.shot_desc_events)
        self.assertIn(7, pipeline_a.character_portrait_events)
        self.assertNotIn(7, pipeline_b.character_portrait_events)

    def test_source_does_not_define_class_level_shared_event_dicts(self):
        class_source = inspect.getsource(Script2VideoPipeline)
        init_source = inspect.getsource(Script2VideoPipeline.__init__)

        self.assertNotIn("character_portrait_events = {}", class_source)
        self.assertNotIn("shot_desc_events = {}", class_source)
        self.assertNotIn("frame_events = {}", class_source)
        self.assertIn("self.character_portrait_events", init_source)
        self.assertIn("self.shot_desc_events", init_source)
        self.assertIn("self.frame_events", init_source)


if __name__ == "__main__":
    unittest.main()
