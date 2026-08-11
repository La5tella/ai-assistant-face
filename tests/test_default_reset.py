import json
from pathlib import Path
import queue
from types import SimpleNamespace
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("pygame", types.ModuleType("pygame"))

from Scripts.clientSideDebugger import llm_response_debugger
from Scripts.clientSideDebugger.llm_response_debugger import LLMResponseDebugger
from Scripts.display.FaceScene import FaceScene


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


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


def rendered_origin(obj):
    return [
        obj.transform.origin_position[axis]
        + obj.position_offset[axis]
        + obj.anim_offset[axis]
        + obj.look_offset[axis]
        for axis in range(2)
    ]


class DefaultTransitionTests(unittest.TestCase):
    def test_thinking_objects_blend_into_default_without_position_snap(self):
        scene = build_scene()
        scene.set_face_state("thinking", duration=0)
        scene.update(0.2)

        left_eye = scene.objects[scene.roles.left_eye_id]
        third_dot = scene.objects[scene.roles.dot_right_id]
        start_origin = rendered_origin(left_eye)
        start_vertices = [vert.local_position.copy() for vert in left_eye.verts]
        third_dot_start_x = abs(third_dot.verts[0].local_position[0])

        scene.set_expression("happy", duration=0)
        self.assertTrue(scene.set_face_state("default", duration=1.0))

        self.assertEqual(rendered_origin(left_eye), start_origin)
        self.assertEqual(
            [vert.local_position for vert in left_eye.verts],
            start_vertices,
        )
        self.assertTrue(left_eye.position_in_transition)
        self.assertTrue(third_dot.active)
        self.assertIn(third_dot, scene.retiring_objects)
        self.assertEqual(scene.current_expression, "neutral")
        self.assertEqual(left_eye.curr_anim, "eye_neutral")

        scene.update(0.5)
        self.assertGreater(left_eye.transform.origin_position[0] + left_eye.position_offset[0], 180)
        self.assertLess(left_eye.transform.origin_position[0] + left_eye.position_offset[0], 300)
        self.assertLess(abs(third_dot.verts[0].local_position[0]), third_dot_start_x)

        scene.update(0.5)
        self.assertEqual(left_eye.position_offset, [0.0, 0.0])
        self.assertFalse(left_eye.position_in_transition)
        self.assertFalse(third_dot.active)
        self.assertNotIn(third_dot, scene.retiring_objects)

    def test_mouth_grows_and_moves_from_thinking_into_default(self):
        scene = build_scene()
        scene.set_face_state("thinking", duration=0)

        mouth = scene.objects[scene.roles.mouth_id]
        self.assertTrue(scene.set_face_state("default", duration=1.0))

        self.assertEqual(rendered_origin(mouth), [360.0, 420.0])
        self.assertTrue(mouth.position_in_transition)
        self.assertTrue(mouth.in_transition)
        self.assertTrue(
            all(vert.local_position == [0.0, 0.0] for vert in mouth.verts)
        )

        scene.update(0.5)
        halfway_origin = rendered_origin(mouth)
        self.assertGreater(halfway_origin[1], 420.0)
        self.assertLess(halfway_origin[1], 540.0)
        self.assertTrue(
            any(vert.local_position != [0.0, 0.0] for vert in mouth.verts)
        )

        scene.update(0.5)
        self.assertEqual(rendered_origin(mouth), [360.0, 540.0])
        self.assertFalse(mouth.position_in_transition)
        self.assertFalse(mouth.in_transition)
        self.assertEqual(mouth.shape_state, "Half-Circle")

    def test_mouth_grows_and_moves_from_thinking_into_speaking(self):
        scene = build_scene()
        scene.set_expression("happy", duration=0)
        scene.set_face_state("thinking", duration=0)

        mouth = scene.objects[scene.roles.mouth_id]
        scene.mouth_manager.curr_syllable = {
            "syllable": "a",
            "time": 0.05,
            "total_time": 1.0,
        }
        scene.mouth_manager.syllable_queue = [
            {"syllable": "o", "time": 0.05, "total_time": 1.0}
        ]

        self.assertTrue(scene.set_face_state("speaking", duration=1.0))

        self.assertIsNone(scene.mouth_manager.curr_syllable)
        self.assertEqual(scene.mouth_manager.syllable_queue, [])
        self.assertEqual(rendered_origin(mouth), [360.0, 420.0])
        self.assertTrue(mouth.position_in_transition)
        self.assertTrue(mouth.in_transition)
        self.assertTrue(
            all(vert.local_position == [0.0, 0.0] for vert in mouth.verts)
        )

        scene.update(1.0)
        self.assertEqual(rendered_origin(mouth), [360.0, 540.0])
        self.assertFalse(mouth.position_in_transition)
        self.assertFalse(mouth.in_transition)
        self.assertEqual(scene.current_expression, "happy")

    def test_default_flushes_speech_gaze_and_expression_state(self):
        scene = build_scene()
        scene.set_face_state("speaking", duration=0)
        scene.set_expression("happy", duration=0)
        scene.set_look_target([1, 0], duration=0)
        scene.mouth_manager.activate_speak(
            [{"syllable": "a", "time": 0.05, "total_time": 1.0}]
        )

        left_eye = scene.objects[scene.roles.left_eye_id]
        mouth = scene.objects[scene.roles.mouth_id]
        self.assertTrue(scene.set_face_state("default", duration=0.5))

        self.assertEqual(scene.current_expression, "neutral")
        self.assertEqual(scene.mouth_manager.syllable_queue, [])
        self.assertIsNone(scene.mouth_manager.curr_syllable)
        self.assertEqual(scene.mouth_manager.time, 0)
        self.assertIsNone(mouth.anim.curr_action)
        self.assertFalse(mouth.anim.action_hold)
        self.assertTrue(mouth.active)
        self.assertEqual(left_eye.curr_anim, "eye_neutral")
        self.assertEqual(left_eye.look_offset, [30.0, 0.0])
        self.assertEqual(left_eye.anim.look_action["target_offset"], [0.0, 0.0])

        scene.update(0.5)
        self.assertEqual(left_eye.look_offset, [0.0, 0.0])
        self.assertFalse(mouth.in_transition)
        self.assertEqual(mouth.shape_state, "Half-Circle")

    def test_debug_reset_uses_zero_duration_for_every_default_transition(self):
        scene = build_scene()
        scene.set_face_state("thinking", duration=0)
        scene.update(0.2)
        scene.set_expression("happy", duration=0)

        self.assertTrue(
            scene.set_face_state(
                "default",
                duration=2.0,
                debug="reset",
            )
        )

        self.assertEqual(scene.current_expression, "neutral")
        self.assertEqual(scene.retiring_objects, set())

        default_positions = {
            scene.roles.mouth_id: [360.0, 540.0],
            scene.roles.left_eye_id: [180.0, 360.0],
            scene.roles.right_eye_id: [540.0, 360.0],
        }
        for object_id, position in default_positions.items():
            obj = scene.objects[object_id]
            self.assertTrue(obj.active)
            self.assertEqual(obj.transform.origin_position, position)
            self.assertEqual(obj.position_offset, [0.0, 0.0])
            self.assertEqual(obj.look_offset, [0.0, 0.0])
            self.assertEqual(obj.transition_duration, 0.0)
            self.assertEqual(obj.anim.transition_time, 0.0)
            self.assertFalse(obj.in_transition)
            self.assertFalse(obj.position_in_transition)

        self.assertFalse(scene.objects[scene.roles.dot_right_id].active)


class DefaultResetDebuggerTests(unittest.TestCase):
    def test_debugger_sends_immediate_default_reset_flag(self):
        debugger = SimpleNamespace(
            host_var=Value("127.0.0.2"),
            port_var=Value(6002),
            log_queue=queue.Queue(),
        )

        with patch.object(llm_response_debugger, "send_commands") as send_commands:
            LLMResponseDebugger._create_and_send_face_state_command(
                debugger,
                "default",
                debug="reset",
            )

        send_commands.assert_called_once_with(
            [{"type": "face_state", "name": "default", "debug": "reset"}],
            host="127.0.0.2",
            port=6002,
        )
        self.assertEqual(
            debugger.log_queue.get_nowait(),
            "Sent face state: default (debug=reset)",
        )


if __name__ == "__main__":
    unittest.main()
