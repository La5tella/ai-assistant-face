import math

class Animation:
    def __init__(self, _obj, _timing_dict, speed=1.0):
        self.obj = _obj
        self.base_y = _obj.transform.origin_position[1]
        self.base_x = _obj.transform.origin_position[0]
        self.timing_dict = _timing_dict
        
        
        self.speed = speed
        self.curr_time = 0
        self.max_time = 1
        if len(_obj.action_queue) != 0:
            self.curr_action = _obj.action_queue[_obj.action_index]
        else:
            self.curr_action = None
        #per-anim data
        self.look_data = [1,1]
        self.amplitude = 10

    def refresh_obj_data(self):
        self.base_y = self.obj.transform.origin_position[1]
        self.base_x = self.obj.transform.origin_position[0]


    def update(self, dt):
        """Before calling, make sure to update the corresponding value. (e.g. Hover needs anim.amplitude to update)"""
        if self.curr_action:
            match self.curr_action:
                case "static":
                    return
                case "hover":
                    self.hover(dt)
                case "blink":
                    self.blink(dt)
                case "look":
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

    def time_check(self):
        if self.time >= self.max_time:
            self.obj.action_index = len(self.obj.action_queue) % self.obj.action_index
            self.update_curr_action()
            

    def update_curr_action(self, action):
        if action is not None:
            self.curr_action = action
        else:
            self.curr_action = self.obj.action_queue[self.obj.action_index]
        self.time = 0