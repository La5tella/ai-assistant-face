import math

class Animation:
    def __init__(self, _obj, speed=1.0):
        self.obj = _obj
        self.base_y = _obj.transform.origin_position[1]
        self.base_x = _obj.transform.origin_position[0]
        
        self.amplitude = 10
        self.speed = speed
        self.time = 0
        self.look_data = [1,1]

    def refresh_obj_data(self):
        self.base_y = self.obj.transform.origin_position[1]
        self.base_x = self.obj.transform.origin_position[0]


    def update(self, anim_type, dt):
        """Before calling, make sure to update the corresponding value. (e.g. Hover needs anim.amplitude to update)"""
        if anim_type is not None:
            match anim_type:
                case "Static":
                    return
                case "Hover":
                    self.hover(dt)
                case "Blink":
                    self.blink(dt)
                case "Look":
                    self.look(self.look_data, dt)
                
    
    def hover(self, dt):
        self.time += dt
        self.obj.transform.origin_position[1] = (
            self.base_y + math.sin(self.time * self.speed) * self.amplitude
        )

    def blink(self, dt):
        print("*blink blink*")

    def look(self, look_data, dt):
        print(f"*looks in direction {look_data}*")
