import pygame
import math


class Transform:

    def __init__(
        self,
        origin_position=[540,540],
        scale=1.0,
        rotation=0.0
    ):

        self.origin_position = origin_position or [0, 0]
        self.scale = scale
        self.rotation = rotation


class Vert:

    def __init__(
        self,
        position=None,
        connected_verts=None,
        target_position=None
    ):

        self.position = position or [0, 0]
        self.connected_verts = connected_verts or []
        self.target_position = target_position or []

class FaceObject:

    def __init__(
        self,
        object_id=0,
        layer=0,
        color=(255, 255, 255),
        shape_state = 'Circle',
        active = True,
        vert_count = 10,
        init_transform = None
    ):

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
        """
        Shape states are used to define what orientation the verticies should be in. Think Blender's Shape keys functionality.
        """
        self.target_state = None
        """
        This is the state that the shape will lerp into. If not None, then it will automatically lerp to that state.
        """

        self.vert_count = vert_count

        self.verts = []

        for i in range(self.vert_count):
            self.verts.append(Vert(position=[0,0]))

        self.apply_shape_state(self.shape_state)

        for i, vert in enumerate(self.verts):
            self.setVertPos(i,vert.target_position)

    def setVertPos(self, id, position):
        self.verts[id].position = position

    def circleOrient(self):
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

    def apply_shape_state(self, shape_state):
        if shape_state == 'Circle':
            self.circleOrient()

    def update_shape_state(self, ease_type, dt):
        self.apply_shape_state(self.shape_state)
        for vert in self.verts:
            if not vert.position == vert.target_position:   
                if ease_type == "linear":
                    vert.position =[self.lerp(vert.position[0],vert.target_position[0], dt), self.lerp(vert.position[1],vert.target_position[1], dt)] 

    def lerp(self, a, b, t):
        return a + (b - a) * t
