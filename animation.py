import math

class Animation:
    def __init__(self, _obj, speed=1.0):
        self.obj = _obj
        self.base_y = _obj.transform.origin_position[1]
        self.base_x = _obj.transform.origin_position[0]
        
        #completion data
        self.curr_time = 0
        self.max_time = 1
        self.completion_type = "time"
        self.anim_count = 0
        self.phase = 0

        """'time' or 'conditional', where conditional completion is defined by anim functions, and time completion is when an action takes a specific time."""

        if len(_obj.action_queue) != 0:
            self.curr_action = _obj.action_queue[_obj.action_index]
        else:
            self.curr_action = None
        
        #per-anim data
        self.look_data = [1,1]
        self.amplitude = 10
        self.speed = speed

    def refresh_obj_data(self):
        self.base_y = self.obj.transform.origin_position[1]
        self.base_x = self.obj.transform.origin_position[0]


    def update(self, dt):
        """Before calling, make sure to update the corresponding value. (e.g. Hover needs anim.amplitude to update)"""
        if self.curr_action:
            done = False
            match self.curr_action["action"]:
                case "static":
                    return
                case "hover":
                    done = self.hover(dt)
                case "blink":
                    done = self.blink(dt)
                case "look":
                    done = self.look(self.look_data, dt)
            if done:
                self.advance_action()
                if self.obj.debug_flag:
                    print("Advancing Action")
    
    def hover(self, dt):
        self.time += dt 
        self.phase += dt * self.speed
        self.obj.transform.origin_position[1] = (
            self.base_y + math.sin(self.phase) * self.amplitude
        )
        return self.phase >= (math.tau * 2) #<--- where '2' is the # of cycles

    def blink(self, dt):
        self.time += dt

        half_duration = 0.5 * self.curr_action["time"]

        # Phase 0: start closing once.
        if self.phase == 0:
            self.obj.transition_timer = 0
            self.obj.transition_duration = half_duration
            self.obj.in_transition = True

            for vert in self.obj.verts:
                vert.target_position[1] = 0

            self.phase = 0.5
            return False

        # Wait for close transition to finish.
        if self.phase == 0.5:
            if not self.obj.in_transition:
                self.phase = 1
            return False

        # Phase 1: start opening once.
        if self.phase == 1:
            self.obj.set_shape_state(
                self.obj.shape_state,
                duration=half_duration
            )

            self.phase = 1.5
            return False

        # Wait for open transition to finish.
        if self.phase == 1.5:
            if not self.obj.in_transition:
                self.phase = 0
                return True

            return False

    def look(self, look_data, dt):
        print(f"*looks in direction {look_data}*")

    def time_check(self):
        return self.time >= self.max_time

    def advance_action(self):
        match self.curr_action["type"]:
            case "conditional":
                self.anim_count += 1
                if self.anim_count >= self.curr_action["count"]:
                    self.obj.action_index = (self.obj.action_index + 1) % len(self.obj.action_queue)
                    self.anim_count = 0
                    self.update_curr_action()
                else:
                    self.update_curr_action(self.curr_action)
            case "time":
                self.obj.action_index = (self.obj.action_index + 1) % len(self.obj.action_queue)
                self.update_curr_action()

    def update_curr_action(self, action=None):
        if action is not None:
            self.curr_action = action
        else:
            self.curr_action = self.obj.action_queue[self.obj.action_index]
        
        self.completion_type = self.curr_action["type"]
        self.time = 0
        self.phase = 0

        if self.completion_type == "time":
            self.max_time = self.curr_action["time"]
        else:
            self.max_time = 999
        
        
                