
class Transform:

    def __init__(
        self,
        origin_position=[0,0],
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
        connected_verts=None
    ):

        self.position = position or [0, 0]
        self.connected_verts = connected_verts or []

class FaceObject:

    def __init__(
        self,
        object_id=0,
        layer=0,
        color="#00D5FF",
        shape_state = 'Circle',
        
        vert_count = 10
    ):

        self.id = object_id

        self.visible = True
        self.active = True

        self.layer = layer

        self.color = color

        self.transform = Transform(origin_position=[0,0])

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

        for i in self.vert_count:
            self.vert_count.append(Vert(position=[0,0]))