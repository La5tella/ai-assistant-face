import json
from pathlib import Path
import queue
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.modules.setdefault("pygame", types.ModuleType("pygame"))

from Scripts.aiIntegration.CommandListener import parse_command_line
from Scripts.aiIntegration.LLMAgentClient import RossbotAgentClient
from Scripts.clientSideDebugger import llm_response_debugger
from Scripts.clientSideDebugger.llm_response_debugger import (
    LLMResponseDebugger,
    build_look_command,
)
from Scripts.display.FaceScene import FaceScene


class FakeCommandClient:
    def __init__(self):
        self.commands = []

    def send_commands(self, commands):
        self.commands.extend(commands)


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def build_scene():
    repo_root = Path(__file__).resolve().parents[1]
    with open(repo_root / "dataLibrary" / "anims.json", encoding="utf-8") as file:
        animations = json.load(file)
    with open(
        repo_root / "dataLibrary" / "expressions.json",
        encoding="utf-8",
    ) as file:
        expressions = json.load(file)
    with open(
        repo_root / "dataLibrary" / "face_states.json",
        encoding="utf-8",
    ) as file:
        face_states = json.load(file)

    scene = FaceScene(
        anim_library=animations,
        expression_data=expressions,
        face_state_data=face_states,
        objCount=5,
        RESOLUTION=[720, 720],
    )
    scene.set_expression("neutral", duration=0)
    scene.set_face_state("default", duration=0)
    return scene


class LookCommandTests(unittest.TestCase):
    def test_listener_accepts_look_command(self):
        command = {"type": "look", "target": [1, 0], "duration": 0.5}

        self.assertEqual(parse_command_line(json.dumps(command)), command)

    def test_agent_client_sends_look_command(self):
        command_client = FakeCommandClient()
        agent = RossbotAgentClient(None, None, command_client)

        agent.look_at([-1, 0.5], duration=0.4, easing="ease-out")

        self.assertEqual(
            command_client.commands,
            [
                {
                    "type": "look",
                    "target": [-1, 0.5],
                    "duration": 0.4,
                    "easing": "ease-out",
                }
            ],
        )

    def test_debugger_builds_normalized_look_command(self):
        self.assertEqual(
            build_look_command("-1", "0.5", "0.4", "ease-out"),
            {
                "type": "look",
                "target": [-1.0, 0.5],
                "duration": 0.4,
                "easing": "ease-out",
            },
        )

    def test_debugger_rejects_out_of_range_look_target(self):
        with self.assertRaisesRegex(ValueError, "between -1 and 1"):
            build_look_command(1.1, 0, 0.25)

    def test_debugger_rejects_invalid_look_fields(self):
        invalid_values = (
            ("right", 0, 0.25, "ease", "must be numeric"),
            (0, 0, -0.1, "ease", "zero or greater"),
            (0, 0, 0.25, "bounce", "Easing must be one of"),
        )

        for target_x, target_y, duration, easing, message in invalid_values:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_look_command(target_x, target_y, duration, easing)

    def test_debugger_preset_updates_fields_and_sends_immediately(self):
        debugger = SimpleNamespace(
            look_x_var=Value("0.0"),
            look_y_var=Value("0.0"),
            _send_look=Mock(),
        )

        LLMResponseDebugger._send_look_preset(debugger, -1.0, 1.0)

        self.assertEqual(debugger.look_x_var.get(), "-1.0")
        self.assertEqual(debugger.look_y_var.get(), "1.0")
        debugger._send_look.assert_called_once_with()

    def test_debugger_sends_look_command_to_selected_connection(self):
        debugger = SimpleNamespace(
            log_queue=queue.Queue(),
        )
        command = build_look_command(1, -0.5, 0.3, "linear")

        with patch.object(llm_response_debugger, "send_commands") as send_commands:
            LLMResponseDebugger._create_and_send_look_command(
                debugger,
                command,
                "127.0.0.2",
                6002,
            )

        send_commands.assert_called_once_with(
            [command],
            host="127.0.0.2",
            port=6002,
        )
        self.assertEqual(
            debugger.log_queue.get_nowait(),
            "Sent look target: [1.0, -0.5]. Duration=0.3. Easing=linear",
        )


class EyeLookAnimationTests(unittest.TestCase):
    def test_look_lerps_both_eyes_without_replacing_ambient_animation(self):
        scene = build_scene()
        left_eye = scene.objects[scene.roles.left_eye_id]
        right_eye = scene.objects[scene.roles.right_eye_id]

        self.assertTrue(scene.set_look_target([1, 0], duration=0.5))
        self.assertEqual(left_eye.curr_anim, "eye_neutral")
        self.assertEqual(right_eye.curr_anim, "eye_neutral")

        scene.update(0.25)
        self.assertAlmostEqual(left_eye.look_offset[0], 15.0)
        self.assertAlmostEqual(right_eye.look_offset[0], 15.0)

        scene.update(0.25)
        self.assertEqual(left_eye.look_offset, [30.0, 0.0])
        self.assertEqual(right_eye.look_offset, [30.0, 0.0])
        self.assertIsNone(left_eye.anim.look_action)
        self.assertIsNone(right_eye.anim.look_action)

    def test_new_target_restarts_from_current_position_without_snapping(self):
        scene = build_scene()
        left_eye = scene.objects[scene.roles.left_eye_id]

        scene.set_look_target([1, 0], duration=1.0)
        scene.update(0.5)
        first_position = left_eye.look_offset[0]

        scene.set_look_target([-1, 0], duration=1.0)

        self.assertEqual(left_eye.look_offset[0], first_position)
        scene.update(0.5)
        self.assertAlmostEqual(left_eye.look_offset[0], -7.5)

    def test_named_look_animation_uses_the_same_lerp(self):
        scene = build_scene()
        left_eye = scene.objects[scene.roles.left_eye_id]
        left_eye.curr_anim = "eye_look_left"

        scene.update(0.25)
        self.assertAlmostEqual(left_eye.look_offset[0], -15.0)

        scene.update(0.25)
        self.assertEqual(left_eye.look_offset, [-30.0, 0.0])

    def test_look_works_in_speaking_state_and_is_rejected_in_thinking(self):
        scene = build_scene()
        scene.set_face_state("speaking", duration=0)

        self.assertTrue(scene.set_look_target([0, -1], duration=0))
        self.assertEqual(
            scene.objects[scene.roles.left_eye_id].look_offset,
            [0.0, -30.0],
        )

        scene.set_face_state("thinking", duration=0)

        self.assertFalse(scene.set_look_target([1, 0]))
        self.assertEqual(
            scene.objects[scene.roles.dot_left_id].look_offset,
            [0.0, 0.0],
        )


if __name__ == "__main__":
    unittest.main()
