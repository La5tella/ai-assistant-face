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
        text_surface = screen.font.render(str(vertId), True, (0, 255, 0))
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
        self.target_state = None
        self.aspect_ratio = aspect_ratio
        self.vert_count = vert_count
        self.vert_debug = vert_debug

        self.verts = []

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
            y = radius * math.sin(theta)
            vert.target_position = [
                center_x + x * cos_rotation - y * sin_rotation,
                center_y + x * sin_rotation + y * cos_rotation
            ]
        
    def rectangleOrient(self):
        """
        This sets the target position's for the verticies into a rectangle pattern.
        """
        width = self.transform.scale * self.aspect_ratio[0]
        height = self.transform.scale * self.aspect_ratio[1]
        side_vert_count = self.vert_count/4
        vert_spacing_w = width/side_vert_count
        vert_spacing_h = width/side_vert_count

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
        for i in range(self.vert_count):
            for j,vert in enumerate(self.verts):
                match i:
                    case 0:
                        vert.target_position = [
                            corners[0][0] - ((i + 1) * (j * vert_spacing_w)),
                            corners[0][1]
                        ]
                    case 1:
                        vert.target_position = [
                            corners[1][0],
                            corners[1][1] + ((i + 1) * (j * vert_spacing_h))
                        ]
                    case 2:
                        vert.target_position = [
                            corners[2][0] + ((i + 1) * (j * vert_spacing_w)),
                            corners[2][1]
                        ]
                    case 3:
                        vert.target_position = [
                            corners[3][0],
                            corners[3][1] - ((i + 1) * (j * vert_spacing_h))
                        ]
                print((i+1)*j)
                pass
       
        

    def triangleOrient(self):
        """
        This sets the target position's for the verticies into a triangle pattern.
        """
        radius = self.transform.scale
        half_width = radius * math.sqrt(3) * 0.5
        half_height = radius * 0.5
        self.polygonOrient([
            [0, -radius],
            [half_width, half_height],
            [-half_width, half_height]
        ])
    #---------------End Shape State Orientation Functions---------------

    def apply_shape_state(self, shape_state):
        """
        Sets the target position based on the shape state. 
            shape_state: 'Circle', 'Square', 'Rectangle', 'Triangle'
        """
        match shape_state:
            case'Circle':
                self.circleOrient()
            case 'Square':
                self.aspect_ratio=[1,1]
                self.rectangleOrient()
            case 'Rectangle':
                self.rectangleOrient()
            case 'Triangle':
                self.triangleOrient()

    def update_shape_state(self, ease_type, dt):
        """
        Eases the shape into it's shape state.
            ease_type: 'linear',
        """
        self.apply_shape_state(self.shape_state)
        for vert in self.verts:
            if not vert.position == vert.target_position:   
                if ease_type == "linear":
                    vert.position =[self.lerp(vert.position[0],vert.target_position[0], dt), self.lerp(vert.position[1],vert.target_position[1], dt)] 

    def lerp(self, a, b, t):
        return a + (b - a) * t
