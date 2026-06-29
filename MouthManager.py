import json
from pathlib import Path

class MouthManager:
    def __init__(self, mouth):
        
        self.mouth = mouth
        
        #Mouth State Library
        self.mouth_lib = None
        with open(Path(__file__).resolve().parent / "dataLibrary/mouth_shapes.json", "r") as file:
            self.mouth_lib = json.load(file)
        if self.mouth_lib == None:
            print("Mouth Shape Library not loaded. Check .json pathing?")
        

        self.syllable_queue = []
        self.curr_syllable = None
        self.time = 0

        self.sample_queue = [
            {"syllable":"a","time":2.0},
            {"syllable":"d","time":2.0},
            {"syllable":"o","time":2.0},
            {"syllable":"f","time":2.0},
            {"syllable":"m","time":2.0},
            {"syllable":"r","time":2.0},
            {"syllable":"s","time":2.0},
            {"syllable":"wo","time":2.0}
            ]

    def activate_speak(self, _syllable_queue=None):
        if _syllable_queue==None:
            _syllable_queue = self.sample_queue
        for syl in _syllable_queue:
            self.syllable_queue.append(syl)
        #test func to activate mouth. Should activate, then auto deactivate
        self.mouth.active = True
        self.start_syllable()
    
    def start_syllable(self):
        self.time = 0

        if len(self.syllable_queue) == 0:
            self.curr_syllable = None
            self.mouth.active = False
            return

        self.curr_syllable = self.syllable_queue.pop(0)
        syl_data = self.mouth_lib[self.curr_syllable["syllable"]]

        self.mouth.transform.scale = syl_data["shape_state"]["scale"]
        self.mouth.set_shape_state(
            shape_state=syl_data["shape_state"]["state"],
            duration=syl_data["anim"]["time"]
        )

        action = syl_data["anim"].copy()
        action["hold_on_complete"] = True
        action["hold_range"] = [0.5, 1.0]
        action["hold_scale"] = syl_data["hold_scale"]
        action["hold_speed"] = 7.5

        self.mouth.action_queue = [action]
        self.mouth.action_index = 0
        self.mouth.anim.update_curr_action(action)
            
        print("Sending action: " + action["action"] + " with time " + str(action["time"]) + " from syllable " + self.curr_syllable["syllable"])
    
    def transition_check(self):
        syllable_time_done = self.time >= self.curr_syllable["time"]
        anim_done = self.mouth.anim.action_done or self.mouth.anim.action_hold
        

        if syllable_time_done and anim_done and self.curr_syllable is not None:
            self.start_syllable()


    def update(self,dt):
        if self.curr_syllable is None:
            return

        self.time += dt
        self.mouth.update(dt)
        self.transition_check()

    def stfu(self):
        self.curr_syllable = None
        self.syllable_queue = []
        self.mouth.active = False

#Notes for tomorrow you:
#Find a way to make the mouth start and end it's activation smoothly.
#Maybe find an anim that blends the mouth into the scene instead of just popping in.
