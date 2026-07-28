from Scripts.display.MouthManager import MouthManager
from Scripts.display.ThinkingManager import ThinkingManager
from Scripts.display.Geometry import Transform, FaceObject

class FaceScene:
    """Coordinates high-level face expression commands across pooled face objects."""
    
    def __init__(self, anim_library, expression_data, face_state_data, objCount, RESOLUTION):
        """Store the drawable objects and expression library used by command handlers."""
        self.expression_data = expression_data
        self.face_state_data = face_state_data
        self.current_expression = None
        self.current_face_state = None
        self.objects = []
        

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

    def set_face_state(self, face_state_name, duration=0.25, easing="ease"):
        """Apply a display mode and hand object ownership to its controllers."""
        states = self.face_state_data.get("states", {})
        if not states:
            print("Unable to load state. Maybe check .json path?")
        state = states.get(face_state_name)
        if state is None:
            print(f"Unknown face state: {face_state_name}")
            return False

        self.current_face_state = face_state_name
        roles = state.get("roles", {})
        thinking_roles = {
            role: role_data
            for role, role_data in roles.items()
            if role_data.get("controller") == "thinking"
        }

        if self.thinking_manager.active:
            self.thinking_manager.deactivate()

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
                easing
            )
            self.objects[obj_index].active = True

        if thinking_roles:
            self.thinking_manager.activate(
                thinking_roles,
                duration,
                easing,
                state.get("sequence_delay"),
            )

        return True

    def apply_object_state(self, obj, state_data, duration=0.25, easing="ease"):
        """Apply one object's state data and start its shape animation if needed."""
        shape_state = state_data.get("shape_state")   

        for attr, value in state_data.items():
            match attr:
                case "scale":
                    obj.transform.scale = value
                case "rotation":
                    obj.transform.rotation = value
                case "position":
                    obj.transform.origin_position = value
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
            if i == 0 and obj.active:
                self.mouth_manager.update(dt)
                self.drawables.append(obj.to_drawable())
            elif obj.active:
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
