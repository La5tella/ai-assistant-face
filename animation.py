import math

class Hover:
    def __init__(self, obj, amplitude=10, speed=1.0):
        self.obj = obj
        self.base_y = obj.transform.origin_position[1]
        self.amplitude = amplitude
        self.speed = speed
        self.time = 0

    def update(self, dt):
        self.time += dt
        self.obj.transform.origin_position[1] = (
            self.base_y + math.sin(self.time * self.speed) * self.amplitude
        )
        self.obj.apply_shape_state(self.obj.shape_state)
