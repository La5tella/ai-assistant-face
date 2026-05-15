import pygame
import math


class Transform:
    """Position, scale, and rotation used to place a face object in the scene."""

    def __init__(
        self,
        origin_position=[540,540],
        scale=1.0,
        rotation=0.0
    ):
        """Create a transform.

        origin_position: Two-item screen-space center position.
        scale: Radius or size multiplier used by shape orientation methods.
        rotation: Rotation in radians applied around origin_position.
        """

        self.origin_position = origin_position or [0, 0]
        self.scale = scale
        self.rotation = rotation


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

        self.shape_state = shape_state
        self.shape_state_lib = ['Circle', 'Square', 'Rectangle', 'Triangle']
        self.shape_state_index = self.shape_state_lib.index(self.shape_state)

        self.target_state = None
        
        self.aspect_ratio = aspect_ratio
        self.vert_count = vert_count
        self.vert_debug = vert_debug
        self.verts = []
        self.transition_timer = 0
        self.in_transition = False

        for i in range(self.vert_count):
            self.verts.append(Vert(position=[0,0]))

        self.apply_shape_state(self.shape_state)
            
        for i, vert in enumerate(self.verts):
            self.setVertPos(i,vert.target_position)

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

        radius = self.transform.scale
        center_x, center_y = self.transform.origin_position
        rotation = self.transform.rotation
        cos_rotation = math.cos(rotation)
        sin_rotation = math.sin(rotation)

        for i, vert in enumerate(self.verts):
            theta = (2 * math.pi * i) / self.vert_count
            x = radius * math.cos(theta)
            y = -radius * math.sin(theta)
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
        

        width = self.transform.scale * (a_ratio[0]/a_ratio[1]) 
        height = self.transform.scale
        

        corners = [
            [
            self.transform.origin_position[0]+(width * .5),self.transform.origin_position[1]-(height * .5)
            ],
            [
            self.transform.origin_position[0]-(width * .5),self.transform.origin_position[1]-(height * .5)
            ],
            [
            self.transform.origin_position[0]-(width * .5),self.transform.origin_position[1]+(height * .5)
            ],
            [
            self.transform.origin_position[0]+(width * .5),self.transform.origin_position[1]+(height * .5)
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
        radius = self.transform.scale
        half_width = radius * math.sqrt(3) * 0.5
        half_height = radius * 0.5
        corners = [
            [self.transform.origin_position[0] + half_width, self.transform.origin_position[1] - half_height],
            [self.transform.origin_position[0] - half_width, self.transform.origin_position[1] - half_height],
            [self.transform.origin_position[0], self.transform.origin_position[1] + radius],
                ]

        self.orientVertsAlongPolygon(corners)
    #---------------End Shape State Orientation Functions---------------

    def cycle_shape_state(self):
        next_index = (self.shape_state_index + 1) % len(self.shape_state_lib)
        self.shape_state = self.shape_state_lib[next_index]
        self.shape_state_index = next_index
        self.transition_timer = 0


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

    def update_shape_state(self, ease_type, duration, dt):
        """
        Eases the shape into it's shape state.
            ease_type: 'linear',
        """
        
        self.apply_shape_state(self.shape_state)
        
        self.transition_timer += dt
        t = self.transition_timer / duration
        t = self.ease_value(ease_type,t)


        for vert in self.verts:
            if vert.position != vert.target_position:
                    vert.position =[self.lerp(vert.position[0],vert.target_position[0], t), self.lerp(vert.position[1],vert.target_position[1], t)] 
                    dx = vert.target_position[0] - vert.position[0]
                    dy = vert.target_position[1] - vert.position[1]

                    if math.sqrt(dx * dx + dy * dy) < .01:
                        vert.position = vert.target_position.copy()
                        

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