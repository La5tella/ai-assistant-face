from math import hypot, isfinite

from Scripts.display.MouthManager import MouthManager
from Scripts.display.ThinkingManager import ThinkingManager
from Scripts.display.Geometry import Transform, FaceObject

class FaceScene:
    """Coordinates high-level face expression commands across pooled face objects."""

    LOOK_OFFSET_RATIO = 0.3
    
    def __init__(self, anim_library, expression_data, face_state_data, objCount, RESOLUTION):
        """Store the drawable objects and expression library used by command handlers."""
        self.expression_data = expression_data
        self.face_state_data = face_state_data
        self.current_expression = None
        self.current_face_state = None
        self.objects = []
        self.retiring_objects = set()
        

        self.drawables = []    
        for i in range(objCount):
            self.objects.append(
                FaceObject(
                    object_id= i,
                    layer= 0,
                    shape_state= 'Circle',
                    color=(113,255,236),
                    aspect_ratio=[16,9],
                    anim_dict=anim_library,
                    vert_count= 32,
                    init_transform=Transform(origin_position=[(RESOLUTION[0]/4)+(i*(RESOLUTION[0]/2)),RESOLUTION[1]/2], scale=[100,100]),
                    debug=False,
                    active=False
                )
            )
        
        self.roles = Roles()
        
        self.mouth_manager = MouthManager(self.objects[self.roles.mouth_id])
        self.thinking_manager = ThinkingManager(
            role_objects={
                "dot_left": self.objects[self.roles.dot_left_id],
                "dot_middle": self.objects[self.roles.dot_middle_id],
                "dot_right": self.objects[self.roles.dot_right_id],
            },
            apply_object_state=self.apply_object_state,
        )

    def handle_ai_command(self, data):
        """Translate AI handler data into a face expression change.

        Expected format:
            {"emotion": "neutral", "duration": 0.25, "easing": "ease"}
        These are the defaults.
        """

        #TODO -- Add a logging function that documents all API call inputs through the handle_ai_command() and stores into ~/logs

        expression_name = data.get("emotion", "neutral")
        if expression_name is None:
            return False

        duration = data.get("duration", 0.25)
        easing = data.get("easing", "ease")
        return self.set_expression(expression_name, duration, easing)

    def set_expression(self, expression_name, duration=0.25, easing="ease"):
        """Apply one named expression from the JSON state library to all listed objects."""
        
        expressions = self.expression_data.get("states", {})
        if not expressions:
            print("Unable to load expressions. Maybe check .json path?")
        expression = expressions.get(expression_name)
        if expression is None:
            print(f"Unknown expression: {expression_name}")
            return False

        self.current_expression = expression_name

        current_state = self.face_state_data.get("states", {}).get(
            self.current_face_state,
            {}
        )
        if current_state and not current_state.get("uses_expression", True):
            return True

        for role in expression:
            obj_index = getattr(self.roles, role + "_id")
            if obj_index >= len(self.objects):
                continue
            
            self.apply_object_state(
                self.objects[obj_index],
                expression[role],
                duration,
                easing
            )
            self.objects[obj_index].active=True

        return True

    def set_look_target(self, target, duration=0.25, easing="ease"):
        """Convert a normalized AI gaze target into eye animation actions.

        ``target`` is an ``[x, y]`` direction where ``[0, 0]`` is centered.
        Values outside the unit circle are normalized so an external command
        cannot move an eye beyond its configured shape radius.
        """
        if (
            not isinstance(target, (list, tuple))
            or len(target) != 2
        ):
            print("Invalid look target: expected a two-item [x, y] list")
            return False

        try:
            target_x = float(target[0])
            target_y = float(target[1])
            duration = float(duration)
        except (TypeError, ValueError):
            print("Invalid look target: coordinates and duration must be numeric")
            return False

        if not all(isfinite(value) for value in (target_x, target_y, duration)):
            print("Invalid look target: coordinates and duration must be finite")
            return False
        if duration < 0:
            print("Invalid look target: duration must be zero or greater")
            return False

        magnitude = hypot(target_x, target_y)
        if magnitude > 1:
            target_x /= magnitude
            target_y /= magnitude

        current_state = self.face_state_data.get("states", {}).get(
            self.current_face_state,
            {},
        )
        state_roles = current_state.get("roles", {})
        eye_count = 0

        for role in ("left_eye", "right_eye"):
            role_state = state_roles.get(role, {})
            if role_state.get("controller") != "eye":
                continue

            obj_index = getattr(self.roles, role + "_id")
            if obj_index >= len(self.objects):
                continue

            obj = self.objects[obj_index]
            if not obj.active:
                continue

            look_radius = min(
                abs(float(obj.transform.scale[0])),
                abs(float(obj.transform.scale[1])),
            ) * self.LOOK_OFFSET_RATIO
            anim_data = {
                "action": "look",
                "type": "conditional",
                "count": 1,
                "target_offset": [
                    target_x * look_radius,
                    target_y * look_radius,
                ],
                "transition_time": duration,
                "easing": easing,
            }
            obj.anim.start_look(anim_data)
            eye_count += 1

        return eye_count > 0

    def set_face_state(
        self,
        face_state_name,
        duration=0.25,
        easing="ease",
        debug=None,
    ):
        """Apply a display mode and hand object ownership to its controllers."""
        states = self.face_state_data.get("states", {})
        if not states:
            print("Unable to load state. Maybe check .json path?")
        state = states.get(face_state_name)
        if state is None:
            print(f"Unknown face state: {face_state_name}")
            return False

        if face_state_name == self.face_state_data.get("default_state", "default"):
            return self.reset_to_default(
                duration=duration,
                easing=easing,
                immediate=debug == "reset",
            )

        roles = state.get("roles", {})
        thinking_roles = {
            role: role_data
            for role, role_data in roles.items()
            if role_data.get("controller") == "thinking"
        }

        self._cancel_retirements()

        was_thinking = self.thinking_manager.active
        mouth_entry_position = None
        mouth_state = roles.get("mouth")
        if (
            was_thinking
            and mouth_state
            and mouth_state.get("active", True)
            and state.get("uses_expression", True)
            and self.current_expression
        ):
            mouth_entry_position = self._thinking_transition_position()

        self.current_face_state = face_state_name

        if self.thinking_manager.active:
            self.thinking_manager.deactivate()

        if mouth_entry_position is not None:
            if duration > 0:
                self.mouth_manager.prepare_transition_in(mouth_entry_position)
            else:
                self.mouth_manager.reset()

        for obj in self.objects:
            obj.active = False

        if state.get("uses_expression", True) and self.current_expression:
            self.set_expression(self.current_expression, duration, easing)

        for role, role_data in roles.items():
            if role in thinking_roles:
                continue

            obj_index = getattr(self.roles, role + "_id")
            if obj_index >= len(self.objects):
                continue

            self.apply_object_state(
                self.objects[obj_index],
                role_data,
                duration,
                easing,
                blend_position=(
                    mouth_entry_position is not None
                    and duration > 0
                    and role == "mouth"
                ),
            )
            self.objects[obj_index].active = True

        if thinking_roles:
            for role in thinking_roles:
                obj_index = getattr(self.roles, role + "_id")
                if obj_index < len(self.objects):
                    self.objects[obj_index].anim.clear_look()

            self.thinking_manager.activate(
                thinking_roles,
                duration,
                easing,
                state.get("sequence_delay"),
            )

        return True

    def reset_to_default(self, duration=0.25, easing="ease", immediate=False):
        """Flush runtime ownership and restore the configured neutral face."""
        default_state_name = self.face_state_data.get("default_state", "default")
        default_state = self.face_state_data.get("states", {}).get(
            default_state_name
        )
        if default_state is None:
            print(f"Unknown default face state: {default_state_name}")
            return False

        try:
            duration = float(duration)
        except (TypeError, ValueError):
            print("Invalid default transition duration")
            return False
        if not isfinite(duration) or duration < 0:
            print("Invalid default transition duration")
            return False
        if immediate:
            duration = 0.0

        mouth_entry_position = None
        if self.thinking_manager.active and duration > 0:
            mouth_entry_position = self._thinking_transition_position()

        previously_active = {obj for obj in self.objects if obj.active}
        previously_retiring = set(self.retiring_objects)
        thinking_objects = set(self.thinking_manager.controlled_objects)
        managed_objects = {self.objects[self.roles.mouth_id]}
        managed_objects.update(thinking_objects)

        self.retiring_objects.clear()
        if mouth_entry_position is not None:
            self.mouth_manager.prepare_transition_in(mouth_entry_position)
        else:
            self.mouth_manager.reset(preserve_visual_position=duration > 0)
        self.thinking_manager.deactivate(
            preserve_visual_position=duration > 0
        )

        for obj in self.objects:
            if obj not in managed_objects:
                if duration > 0:
                    obj.preserve_animation_offset()
                obj.curr_anim = None

            obj.anim.clear_look(reset_position=duration == 0)
            obj.active = False

            if duration == 0:
                obj.clear_position_transition()

        self.current_face_state = default_state_name
        default_expression = default_state.get(
            "expression",
            self.expression_data.get("default_state", "neutral"),
        )
        if not self.set_expression(default_expression, duration, easing):
            return False

        target_objects = set()
        for role, role_data in default_state.get("roles", {}).items():
            obj_index = getattr(self.roles, role + "_id")
            if obj_index >= len(self.objects):
                continue

            obj = self.objects[obj_index]
            target_objects.add(obj)
            self.apply_object_state(
                obj,
                role_data,
                duration,
                easing,
                blend_position=True,
            )
            obj.active = True

        self.set_look_target([0.0, 0.0], duration, easing)

        for obj in (previously_active | previously_retiring) - target_objects:
            obj.anim.clear_look()
            obj.transform.scale = [0.0, 0.0]
            obj.set_shape_state(obj.shape_state, duration, easing)

            if duration == 0:
                obj.active = False
                obj.clear_position_transition()
                continue

            obj.active = True
            self.retiring_objects.add(obj)

        if duration == 0:
            for obj in self.objects:
                obj.anim.transition_time = 0.0

        return True

    def _thinking_transition_position(self):
        """Return the visible center of the objects owned by thinking mode."""
        controlled_objects = self.thinking_manager.controlled_objects
        if not controlled_objects:
            position = self.objects[
                self.roles.mouth_id
            ].transform.origin_position
            return [float(position[0]), float(position[1])]

        return [
            sum(
                float(obj.transform.origin_position[axis])
                + obj.position_offset[axis]
                + obj.anim_offset[axis]
                for obj in controlled_objects
            ) / len(controlled_objects)
            for axis in range(2)
        ]

    def _cancel_retirements(self):
        for obj in self.retiring_objects:
            obj.active = False
        self.retiring_objects.clear()

    def apply_object_state(
        self,
        obj,
        state_data,
        duration=0.25,
        easing="ease",
        blend_position=False,
    ):
        """Apply one object's state data and start its shape animation if needed."""
        shape_state = state_data.get("shape_state")   

        for attr, value in state_data.items():
            match attr:
                case "scale":
                    obj.transform.scale = value
                case "rotation":
                    obj.transform.rotation = value
                case "position":
                    if blend_position:
                        obj.set_origin_position(value, duration, easing)
                    else:
                        obj.transform.origin_position = [
                            float(value[0]),
                            float(value[1]),
                        ]
                        obj.clear_position_transition()
                case "active":
                    obj.active = value
                case "ambient_anim":
                    obj.curr_anim = value
        
        if shape_state is not None:
            obj.set_shape_state(shape_state, duration, easing)
        else:
            obj.apply_shape_state(obj.shape_state)

    def drawables(self):
        return sorted(
            (obj.to_drawable() for obj in self.objects.values() if obj.active),
            key=lambda drawable: drawable.layer,
        )

    def update(self, dt):
        """Advance animation for every active object in the scene."""
        self.drawables = []
        for i, obj in enumerate(self.objects):
            if not obj.active:
                continue

            if obj in self.retiring_objects:
                obj.update(dt)
                if not obj.in_transition and not obj.position_in_transition:
                    obj.active = False
                    obj.clear_position_transition()
                    self.retiring_objects.remove(obj)
                    continue
                self.drawables.append(obj.to_drawable())
            elif i == self.roles.mouth_id:
                self.mouth_manager.update(dt)
                self.drawables.append(obj.to_drawable())
            else:
                obj.update(dt)
                self.drawables.append(obj.to_drawable())

        
class Roles:
    """Map semantic roles onto reusable objects in the scene pool."""

    def __init__(self, mouth=0, l_eye=1, r_eye=2, thinking_dot=3):
        self.mouth_id = mouth
        self.left_eye_id = l_eye
        self.right_eye_id = r_eye
        self.dot_left_id = l_eye
        self.dot_middle_id = r_eye
        self.dot_right_id = thinking_dot
