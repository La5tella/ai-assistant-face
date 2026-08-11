import math

class Animation:
    def __init__(self, _obj, speed=1.0):
        self.obj = _obj
        #completion data
        self.transition_time = 0.025
        self.max_time = 1
        self.completion_type = "time"
        self.anim_count = 0
        self.phase = 0
        self.start_delay = 0
        self.time = 0
        
        self.action_done = False
        self.action_hold = False
        self.action_hold_time = 0
        self.action_end_positions = {"Max":[], "Min":[]}

        """'time' or 'conditional', where conditional completion is defined by anim functions, and time completion is when an action takes a specific time."""

        if len(_obj.action_queue) != 0:
            self.curr_action = _obj.action_queue[_obj.action_index]
        else:
            self.curr_action = None
        
        #per-anim data
        self.look_action = None
        self.look_start_position = [0.0, 0.0]
        self.look_time = 0.0
        self.amplitude = 10
        self.speed = speed

        self.constanant_timer = 0
        self.debug_timer = 0

    def reset_runtime(self):
        """Clear the current action without changing the object's visible shape."""
        self.curr_action = None
        self.transition_time = 0.025
        self.max_time = 1
        self.completion_type = "time"
        self.anim_count = 0
        self.phase = 0
        self.start_delay = 0
        self.time = 0
        self.action_done = False
        self.action_hold = False
        self.action_hold_time = 0
        self.action_end_positions = {"Max": [], "Min": []}
        self.constanant_timer = 0
        self.debug_timer = 0
        self.obj.anim_offset = [0.0, 0.0]

    def update(self, dt):
        """Before calling, make sure to update the corresponding value. (e.g. Hover needs anim.amplitude to update)"""
        # Gaze is a parallel animation channel so eye hover/blink actions can
        # continue while the eyes move toward an AI-provided target.
        self.update_look(dt)

        if self.start_delay > 0:
            delayed_time = min(dt, self.start_delay)
            self.start_delay -= delayed_time
            dt -= delayed_time
            if dt <= 0:
                return

        self.debug_timer +=dt
        if self.action_hold:
            self.hold_action(dt)
            return

        if self.curr_action:
            done = False
            self.time += dt
            match self.curr_action["action"]:
                case "static":
                    done = not self.obj.in_transition
                case "hover":
                    done = self.hover(dt)
                case "blink":
                    done = self.blink(dt)
                case "look":
                    done = self.look(self.curr_action, dt)
                case "think":
                    done = self.think(dt)
                case "constanant_close":
                    done = self.constanant_close(dt)
            if done:
                if self.curr_action.get("hold_on_complete"):
                    self.action_hold = True
                    self.action_done = True
                    self.hold_action(dt)
                    if self.obj.debug_flag:
                        print("Holding Action")
                else:
                    self.action_done = True
                    self.advance_action()
                    if self.obj.debug_flag:
                        print("Advancing Action")
    
    def hover(self, dt): 
        self.phase += dt * self.speed
        self.obj.anim_offset[1] = (math.sin(self.phase) * self.amplitude)
        return self.phase >= (math.tau * 2) #<--- where '2' is the # of cycles

    def blink(self, dt):
        half_duration = 0.5 * self.transition_time

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

    def start_look(self, action):
        """Start or replace a gaze transition from an animation action."""
        target_offset = action.get("target_offset")
        if (
            not isinstance(target_offset, (list, tuple))
            or len(target_offset) != 2
        ):
            raise ValueError("look action requires a two-item target_offset")

        transition_time = max(float(action.get("transition_time", 0.25)), 0.0)
        self.look_action = dict(action)
        self.look_action["target_offset"] = [
            float(target_offset[0]),
            float(target_offset[1]),
        ]
        self.look_action["transition_time"] = transition_time
        self.look_start_position = self.obj.look_offset.copy()
        self.look_time = 0.0

        if transition_time == 0:
            self.obj.look_offset = self.look_action["target_offset"].copy()
            self.look_action = None

    def update_look(self, dt):
        """Lerp the object's gaze offset without interrupting its ambient action."""
        if self.look_action is None:
            return

        transition_time = self.look_action["transition_time"]
        self.look_time = min(self.look_time + dt, transition_time)
        completion = self.look_time / transition_time
        completion = self.obj.ease_value(
            self.look_action.get("easing", "ease"),
            completion,
        )
        target_offset = self.look_action["target_offset"]

        self.obj.look_offset = [
            self.obj.lerp(
                self.look_start_position[axis],
                target_offset[axis],
                completion,
            )
            for axis in range(2)
        ]

        if self.look_time >= transition_time:
            self.obj.look_offset = target_offset.copy()
            self.look_action = None

    def clear_look(self, reset_position=True):
        """Cancel gaze ownership, optionally returning the object to center."""
        self.look_action = None
        self.look_time = 0.0
        if reset_position:
            self.obj.look_offset = [0.0, 0.0]
        self.look_start_position = self.obj.look_offset.copy()

    def look(self, look_data, dt):
        """Run a named look action through the same gaze channel."""
        if self.phase == 0:
            self.start_look(look_data)
            self.update_look(dt)
            self.phase = 1

        if self.look_action is None:
            self.phase = 0
            return True

        return False

    def think(self, dt):
        """Move one thinking dot through a continuous, smoothly looping hop."""
        cycle_duration = max(
            float(self.curr_action.get("transition_time", 0.6)),
            0.001,
        )
        amplitude = float(self.curr_action.get("amplitude", self.amplitude))

        self.phase = (
            self.phase + (math.tau * dt / cycle_duration)
        ) % math.tau
        self.obj.anim_offset[1] = (
            -amplitude * (1 - math.cos(self.phase)) * 0.5
        )

        # Thinking is an ambient animation. The manager stops it explicitly
        # when another face state takes ownership of the eyes.
        return False

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
        
        self.obj.anim_offset=[0,0]
        self.action_hold = False
        self.action_done = False
        self.start_delay = 0
        self.completion_type = self.curr_action["type"]
        self.time = 0
        self.phase = 0
        self.constanant_timer = 0
        self.action_hold_time = 0
        self.action_end_positions = {"Max":[], "Min":[]}
        # print(str(self.curr_action["action"]) + " action took " + str(self.debug_timer) + " to complete")
        self.debug_timer = 0
        if self.completion_type == "time":
            self.max_time = self.curr_action["time"]
            try:
                self.transition_time = self.curr_action["transition_time"]
            except KeyError:
                self.transition_time = 0
        else:
            self.max_time = 999
        
    def hold_action(self, dt=0):
        
        if not self.curr_action:
            return
    
        if len(self.action_end_positions["Max"]) == 0:
            hold_max_positions = [
                vert.local_position.copy()
                for vert in self.obj.verts
            ]
            self.action_end_positions["Max"] = hold_max_positions
            

        hold_range = self.curr_action.get("hold_range", [1.0, 1.0])
        hold_speed = self.curr_action.get("hold_speed", 1.0)
    
        low = hold_range[0]
        high = hold_range[1]
    
        self.action_hold_time += dt * hold_speed
    
        # Oscillates smoothly 0 -> 1 -> 0.
        wave = (math.sin(self.action_hold_time * math.tau) + 1) * 0.5
    
        # Convert wave into range, e.g. 0.95 -> 1.0.
        completion = low + ((high - low) * wave)
    
        if len(self.action_end_positions["Min"]) == 0:
            #calculation for end positions
            hold_scale = self.curr_action.get("hold_scale",[.8,.8])
            hold_min_positions = [
                vert.local_position.copy() 
                for vert in self.obj.verts
            ] 
            for i, local_pos in enumerate(hold_min_positions):
                scaled_pos = [
                    local_pos[0]*hold_scale[0],
                    local_pos[1]*hold_scale[1]
                ]
                self.action_end_positions["Min"].append(scaled_pos)

        if len(self.action_end_positions["Min"]) != 0 and len(self.action_end_positions["Max"]) != 0:
            for i, vert in enumerate(self.obj.verts):
                vert.local_position = [
                    self.obj.lerp(self.action_end_positions["Min"][i][0], self.action_end_positions["Max"][i][0], completion),
                    self.obj.lerp(self.action_end_positions["Min"][i][1], self.action_end_positions["Max"][i][1], completion)
                    ]
                
    def constanant_close(self, dt):
        half_time = self.curr_action["transition_time"] * 0.5
        
        self.constanant_timer += dt
        
        match self.phase:
            case 0:
                for vert in self.obj.verts:
                    vert.target_position = [
                        vert.local_position[0],
                        0
                    ]
            
                self.obj.transition_timer = 0
                self.obj.transition_duration = half_time
                self.obj.in_transition = True
            
                self.phase = 0.5
                return False
            
            case 0.5:
                if not self.obj.in_transition:
                    self.obj.set_shape_state(
                        self.obj.shape_state,
                        duration=half_time
                    )
                    self.phase = 1
            
                return False
            
            case 1:
                if not self.obj.in_transition:
                    self.phase = 0
                    return True
            
                return False
