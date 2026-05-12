
class Transform:
    originPosition = [0,0]
    scale = 1
    rotation = 1


class Verts:
    position = [0,0]
    connectedVerts=[0]

class FaceObject:
    id = 0
    visible = True
    active = True
    layer = 0
    transform = [0,0]
    color = "#00D5FF"
    shapeState = None
    targetState = None
    verts = [Verts]
    vertCount = 0
    transform = Transform
