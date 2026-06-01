import pygame
from MouthManager import MouthManager
import math
from animation import Animation

class Transform:
    """Position, scale, and rotation used to place a face object in the scene."""

    def __init__(
        self,
        origin_position=[540,540],
        scale=[1.0,1.0],
        rotation=0.0
    ):
        """Create a transform.

        origin_position: Two-item screen-space center position.
        scale: Radius or size multiplier used by shape orientation methods.
        rotation: Rotation in degrees applied around origin_position.
        """

        self.origin_position = origin_position or [0, 0]
        self.scale = scale
        self.rotation = rotation

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, degrees):
        self._rotation = math.radians(degrees)


class Vert:
    """A vertex with a current position, neighbor links, and an animation target."""

    def __init__(
        self,
        position=None,
        connected_verts=None,
        target_position=None
    ):
        """Create a vertex.

        position: Current two-item screen-space position.
        connected_verts: Other vertices connected to this vertex.
        target_position: Destination position used when easing shape states.
        """

        self.local_position = position or [0, 0]
        self.position = position or [0, 0]
        self.connected_verts = connected_verts or []
        self.target_position = target_position or []

    def draw_vert_debug(self, vertId, screen):
        text_surface = screen.fonts[0].render(str(vertId), True, (0, 255, 0))
        screen.screen.blit(text_surface, self.position)

class FaceObject:
    """A drawable shape made from vertices and driven by named shape states."""

    def __init__(
        self,
        object_id=0,
        layer=0,
        color=(255, 255, 255),
        shape_state = 'Circle',
        anim_dict = {},
        aspect_ratio = [1,1],
        active = True,
        vert_count = 10,
        init_transform = None,
        vert_debug = False
    ):
        """Create a face object.

        object_id: Stable identifier for the shape.
        layer: Draw ordering value.
        color: RGB color tuple used when rendering.
        shape_state: Named vertex layout to apply, such as 'Circle'.
        aspect_ratio: Aspect ratio used for rectangular shapes
        active: Initial active and visible state.
        vert_count: Number of vertices to allocate.
        init_transform: Optional Transform overriding the default placement.
        vert_debug: draw vert debug?
        """
        
        self.id = object_id

        self.visible = active
        self.active = active

        self.layer = layer

        self.color = color
        if init_transform == None:
            self.transform = Transform()
        else:
            self.transform = init_transform

        self.target_state = None
        
        self.aspect_ratio = aspect_ratio
        self.vert_count = vert_count
        self.vert_debug = vert_debug
        self.verts = []
        self.transition_timer = 0
        self.transition_duration = 0.25
        self.ease_type = "ease"
        self.in_transition = False

        self.debug_flag=False
        
        self._curr_anim = None
        self.anim_dict = anim_dict
        self.action_index = 0
        self.action_queue = []
        self.anim = Animation(self)
        

        self.shape_state_lib = ['Circle', 'Square', 'Rectangle', 'Triangle', 'Half-Circle']
        self._shape_state = None
        self.shape_state_index = 0


        for i in range(self.vert_count):
            self.verts.append(Vert(position=[0,0]))

        self.set_shape_state(shape_state, duration=0)

    @property
    def curr_anim(self):
        return self._curr_anim

    @curr_anim.setter
    def curr_anim(self, value):
        """
        This should update the animation's time value
        """
        if value != None:
            self.action_queue = self.anim_dict["anims"][value]
            self.action_index = 0
            self.anim.update_curr_action(self.action_queue[self.action_index])
            
        self._curr_anim = value
        
    
    @property
    def shape_state(self):
        return self._shape_state

    @shape_state.setter
    def shape_state(self, value):
        """
        This ensures that when the shape state changes, it automatically triggers apply_state_shape and opens the gate for update_state_shape to work
        """
        if value not in self.shape_state_lib:
            raise ValueError(f"Invalid shape_state: {value}")
        
        self.set_shape_state(value)
        self.anim.refresh_obj_data()

    def setVertPos(self, id, position):
        """
        Directly sets the vertex's positions. Useful for immediate changes/setups.
        """
        self.verts[id].position = position

    #-----------------Shape State Orientation Functions-----------------
    def circleOrient(self):
        """
        This sets the target position's for the verticies into a circular pattern.
        """
        if self.vert_count <= 0:
            return

        radius = 1
        center_x, center_y = [0,0]
        rotation = self.transform.rotation
        cos_rotation = math.cos(rotation)
        sin_rotation = math.sin(rotation)

        for i, vert in enumerate(self.verts):
            theta = (2 * math.pi * i) / self.vert_count
            x = self.transform.scale[0] * radius * math.cos(theta)
            y = self.transform.scale[1] * -radius * math.sin(theta)
            vert.target_position = [
                center_x + x * cos_rotation - y * sin_rotation,
                center_y + x * sin_rotation + y * cos_rotation
            ]
        
    def halfCircleOrient(self):
        """
        This sets the target positions for the vertices into a half-circle pattern.
        """
        if self.vert_count <= 0:
            return

        radius = 1
        scale_x = self.transform.scale[0]
        scale_y = self.transform.scale[1]
        center_x, center_y = [0, 0]
        rotation = self.transform.rotation
        cos_rotation = math.cos(rotation)
        sin_rotation = math.sin(rotation)

        if self.vert_count == 1:
            self.verts[0].target_position = [center_x, center_y - scale_y * radius]
            return

        arc_count = max(1, self.vert_count // 2)
        line_count = self.vert_count - arc_count

        for i in range(arc_count):
            theta = (math.pi * i) / max(1, arc_count - 1)
            x = scale_x * radius * math.cos(theta)
            y = scale_y * -radius * math.sin(theta)
            vert = self.verts[i]
            vert.target_position = [
                center_x + x * cos_rotation - y * sin_rotation,
                center_y + x * sin_rotation + y * cos_rotation
            ]

        for i in range(line_count):
            t = i / max(1, line_count - 1)
            x = -scale_x * radius + (scale_x * radius * 2 * t)
            y = 0
            vert = self.verts[arc_count + i]
            vert.target_position = [
                center_x + x * cos_rotation - y * sin_rotation,
                center_y + x * sin_rotation + y * cos_rotation
            ]

    def orientVertsAlongPolygon(self, corners):
        if len(corners) < 2:
            return

        if len(self.verts) <= 0:
            return

        corner_count = len(corners)
        vert_count = len(self.verts)

        # If there are fewer verts than corners, fall back to simple perimeter sampling.
        # You cannot preserve every corner if you do not have enough verts.
        if vert_count < corner_count:
            return

        verts_per_side = vert_count // corner_count
        leftover_verts = vert_count % corner_count

        vert_index = 0

        for side_index in range(corner_count):
            start = corners[side_index]
            end = corners[(side_index + 1) % corner_count]

            side_vert_count = verts_per_side

            if side_index < leftover_verts:
                side_vert_count += 1

            for i in range(side_vert_count):
                if vert_index >= vert_count:
                    return

                t = i / side_vert_count

                x = start[0] + (end[0] - start[0]) * t
                y = start[1] + (end[1] - start[1]) * t

                self.verts[vert_index].target_position = [x, y]
                vert_index += 1

    def rectangleOrient(self, a_ratio=None):
        """
        This sets the target position's for the verticies into a rectangle pattern.
        """
        if a_ratio == None: a_ratio=self.aspect_ratio
        

        width = self.transform.scale[0] * (a_ratio[0]/a_ratio[1]) 
        height = self.transform.scale[1]
        

        corners = [
            [
            (width * .5),-(height * .5)
            ],
            [
            -(width * .5),-(height * .5)
            ],
            [
            -(width * .5),+(height * .5)
            ],
            [
            +(width * .5),+(height * .5)
            ]
        ]
        """
        corners: (-,-),(+,-),(-,+),(+,+)
        """
        self.orientVertsAlongPolygon(corners)
        
    def triangleOrient(self):
        """
        This sets the target position's for the verticies into a triangle pattern.
        """
        radius = 1
        half_width = self.transform.scale[0] * radius * math.sqrt(3) * 0.5
        half_height = self.transform.scale[1] * radius * 0.5
        corners = [
            [half_width,-half_height],
            [-half_width,-half_height],
            [0,self.transform.scale[1] * radius],
                ]

        self.orientVertsAlongPolygon(corners)
    #---------------End Shape State Orientation Functions---------------

    #-----------------Shape State Application Functions-----------------
    def cycle_shape_state(self):
        
        next_index = (self.shape_state_index + 1) % len(self.shape_state_lib)
        self.set_shape_state(self.shape_state_lib[next_index])
        
    def set_shape_state(self, shape_state, duration=0.25, easing="ease"):
        if shape_state not in self.shape_state_lib:
            raise ValueError(f"Invalid shape_state: {shape_state}")

        self._shape_state = shape_state
        self.shape_state_index = self.shape_state_lib.index(shape_state)
        self.transition_timer = 0
        self.transition_duration = max(duration, 0)
        self.ease_type = easing
        self.apply_shape_state(shape_state)

        if self.transition_duration == 0:
            for vert in self.verts:
                vert.local_position = vert.target_position.copy()
            self.in_transition = False
        else:
            self.in_transition = True

    def apply_shape_state(self, shape_state):
        """
        Sets the target position based on the shape state. 
            shape_state: 'Circle', 'Square', 'Rectangle', 'Triangle'
        """
        match shape_state:
            case'Circle':
                self.circleOrient()
            case 'Square':
                self.rectangleOrient([1,1])
            case 'Rectangle':
                self.rectangleOrient()
            case 'Triangle':
                self.triangleOrient()
            case 'Half-Circle':
                self.halfCircleOrient()

    def update_shape_state(self, ease_type=None, duration=None, dt=0):
        """
        Eases the shape into it's shape state.
            ease_type: 'linear','ease-in','ease-out','ease'

        """
        if self.in_transition:
            if ease_type != None:
                self.ease_type = ease_type

            if duration != None:
                self.transition_duration = duration
                
            if self.transition_duration == 0:
                for vert in self.verts:
                    vert.local_position = vert.target_position.copy()
                self.in_transition = False
                self.debug_movement(1)
                return

            self.transition_timer += dt
            t = self.transition_timer / self.transition_duration
            t = self.ease_value(self.ease_type,t)

            self.in_transition = False

            for vert in self.verts:
                if vert.local_position != vert.target_position:
                        vert.local_position =[self.lerp(vert.local_position[0],vert.target_position[0], t), self.lerp(vert.local_position[1],vert.target_position[1], t)] 
                        dx = vert.target_position[0] - vert.local_position[0]
                        dy = vert.target_position[1] - vert.local_position[1]

                        if math.sqrt(dx * dx + dy * dy) < .01:
                            vert.local_position = vert.target_position.copy()
                        else:
                            self.in_transition = True
                        
                self.debug_movement(t)
       
    #---------------End Shape State Orientation Functions---------------
    #------------------------Animation Functions------------------------
    def update(self, dt):
        
        self.update_shape_state(dt=dt)
        self.anim.update(dt=dt)
        self.update_global_position()
        
                    
    def lerp(self, a, b, t):
        return a + (b - a) * t

    def ease_value(self, ease_type, t):
        t = max(0, min(1, t))

        match ease_type:
            case "linear":
                return t

            case "ease-in":
                return t * t

            case "ease-out":
                return 1 - (1 - t) * (1 - t)

            case "ease":
                return t * t * (3 - 2 * t)  # smoothstep

            case _:
                return t
            
    def update_global_position(self):
        for vert in self.verts:
            vert.position[0] = vert.local_position[0] + self.transform.origin_position[0]
            vert.position[1] = vert.local_position[1] + self.transform.origin_position[1]
    #----------------------End Animation Functions---------------------- 


    def debug_movement(self,t):
        if self.in_transition:
            self.color = (self.lerp(225, 0, t), self.lerp(0, 225, t), 0)
        else:
            self.colorv = (0, 225, 0)


class FaceScene:
    """Coordinates high-level face expression commands across pooled face objects."""
    
    def __init__(self, objects, expression_data):
        """Store the drawable objects and expression library used by command handlers."""
        self.objects = objects
        self.expression_data = expression_data
        self.current_expression = None

        self.mouth_manager = MouthManager(objects[0])
        objects[0].debug_flag = True
        
        """objects[0] will always be mouth."""

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

        for obj_id, state_data in expression.items():
            obj_index = int(obj_id)
            if obj_index >= len(self.objects):
                continue

            self.apply_object_state(
                self.objects[obj_index],
                state_data,
                duration,
                easing
            )

        return True

    def apply_object_state(self, obj, state_data, duration=0.25, easing="ease"):
        """Apply one object's state data and start its shape animation if needed."""
        shape_state = state_data.get("shape_state")   

        for attr, value in state_data.items():
            if attr == "transform":
                for atr, val in value.items():
                    setattr(obj.transform, atr, val) #<<<<<<<
            elif attr == 'anim':
                obj.curr_anim = value
            else:
                setattr(obj, attr, value)
        
        if shape_state is not None:
            obj.set_shape_state(shape_state, duration, easing)
        else:
            obj.apply_shape_state(obj.shape_state)

    def update(self, dt):
        """Advance animation for every active object in the scene."""
        
        for i, obj in enumerate(self.objects):
            if i == 0 and obj.active:
                self.mouth_manager.update(dt)
            elif obj.active:
                obj.update(dt)
        
