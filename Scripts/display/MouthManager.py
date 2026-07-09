import json
from pathlib import Path

class MouthManager:
    def __init__(self, mouth):
        
        self.mouth = mouth
        
        #Mouth State Library
        self.mouth_lib = None
        with open(Path(__file__).resolve().parents[2] / "dataLibrary" / "mouth_shapes.json", "r") as file:
            self.mouth_lib = json.load(file)
        if self.mouth_lib == None:
            print("Mouth Shape Library not loaded. Check .json pathing?")
        

        self.syllable_queue = []
        self.curr_syllable = None
        self.time = 0

        self.sample_queue = [
            {"syllable":"a","time":0.05,"total_time":2.0},
            {"syllable":"d","time":0.05,"total_time":2.0},
            {"syllable":"o","time":0.05,"total_time":2.0},
            {"syllable":"f","time":0.05,"total_time":2.0},
            {"syllable":"m","time":0.05,"total_time":2.0},
            {"syllable":"r","time":0.05,"total_time":2.0},
            {"syllable":"s","time":0.05,"total_time":2.0},
            {"syllable":"wo","time":0.05,"total_time":0.35}
            ]

    def activate_speak(self, _syllable_queue=None):
        if _syllable_queue==None:
            self.syllable_queue = []
            for payload in self.sample_queue:
                self.syllable_queue.append(payload.copy())
        else:
            self.syllable_queue = _syllable_queue
        #test func to activate mouth. Should activate, then auto deactivate
        self.mouth.transform.scale = [1,0]
        self.mouth.shape_state = "Circle"
        
        self.syllable_queue.append({"syllable":"neutral","time":0.05, "total_time":0.05})
        self.mouth.active = True
        self.start_syllable()
    
    def start_syllable(self, initial_time=0):
        self.time = initial_time

        if len(self.syllable_queue) == 0:
            self.curr_syllable = None
            self.mouth.active = False
            return

        self.curr_syllable = self.syllable_queue.pop(0)

        if self.curr_syllable["syllable"] == "wait":
            return
    
        syl_data = self.mouth_lib[self.curr_syllable["syllable"]]
        transition_time = self.curr_syllable["time"]

        self.mouth.transform.scale = syl_data["shape_state"]["scale"]
        self.mouth.set_shape_state(
            shape_state=syl_data["shape_state"]["state"],
            duration=transition_time
        )

        action = syl_data["anim"].copy()
        action["hold_on_complete"] = True
        action["hold_range"] = [0.5, 1.0]
        action["hold_scale"] = syl_data["hold_scale"]
        action["hold_speed"] = 7.5
        action["transition_time"] = transition_time
        action["time"] = self.curr_syllable["total_time"]

        self.mouth.action_queue = [action]
        self.mouth.action_index = 0
        self.mouth.anim.update_curr_action(action)
            
        #print("Sending action: " + action["action"] + " with time " + str(action["transition_time"]) + "/" + str(action["time"]) + " from syllable " + self.curr_syllable["syllable"])
    
    def transition_check(self):
        syllable_time_done = self.time >= self.curr_syllable["total_time"]
        if self.curr_syllable["syllable"] == "wait":
            anim_done = True
        else:
            anim_done = self.mouth.anim.action_done or self.mouth.anim.action_hold
        #print(
        #    self.curr_syllable["syllable"],
        #    "mouth_time", self.time,
        #    "transition/total",
        #    self.curr_syllable["time"],
        #    self.curr_syllable["total_time"],
        #    "anim_done", self.mouth.anim.action_done,
        #    "hold", self.mouth.anim.action_hold,
        #    "in_transition", self.mouth.in_transition
        #    )

        if syllable_time_done and anim_done and self.curr_syllable is not None:
            overshoot = self.time - self.curr_syllable["total_time"]
            self.start_syllable(overshoot)


    def update(self,dt):
        if self.curr_syllable is None:
            return

        self.time += dt
        if self.curr_syllable["syllable"] != "wait":
            self.mouth.update(dt)
        self.transition_check()

    def stfu(self):
        self.curr_syllable = None
        self.syllable_queue = []
        self.mouth.active = False
