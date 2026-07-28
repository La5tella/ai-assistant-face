from Scripts.display.MouthManager import MouthManager
from Scripts.display.animation import Animation
from Scripts.display.Geometry import Vert, Transform, FaceObject
from dataclasses import dataclass

class FaceScene:
    """Coordinates high-level face expression commands across pooled face objects."""
    
    def __init__(self, anim_library, expression_data, face_state_data, objCount, RESOLUTION):
        """Store the drawable objects and expression library used by command handlers."""
        self.expression_data = expression_data
        self.face_state_data = face_state_data
        self.current_expression = None
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
        if expressions is {}:
            print("Unable to load expressions. Maybe check .json path?")
        expression = expressions.get(expression_name)
        if expression is None:
            print(f"Unknown expression: {expression_name}")
            return False

        self.current_expression = expression_name

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
            """Apply one named expression from the JSON state library to all listed objects."""
            
            states = self.face_state_data.get("states", {})
            if states is {}:
                print("Unable to load state. Maybe check .json path?")
            state = states.get(face_state_name)
            if state is None:
                print(f"Unknown expression: {face_state_name}")
                return False
    
            self.current_expression = face_state_name

            roles =state["roles"]
            for role in roles:
                obj_index = getattr(self.roles, role + "_id")
                if obj_index >= len(self.objects):
                    continue
                
                self.apply_object_state(
                    self.objects[obj_index],
                    roles[role],
                    duration,
                    easing
                )
                self.objects[obj_index].active=True
    
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

        
@dataclass
class Roles:
    def __init__(self, mouth=0, l_eye=1,r_eye=2):
        self.mouth_id = mouth
        self.left_eye_id = l_eye
        self.right_eye_id = r_eye