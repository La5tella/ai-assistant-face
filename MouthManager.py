import FaceScene
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
        
        self.sample_queue = [
            {"syllable":"a","time":0.3},
            {"syllable":"o","time":0.5},
            {"syllable":"wo","time":0.1}
            ]

    def activate_speak(self, syllable_queue=None, ):
        if syllable_queue==None:
            self.syllable_queue.append(self.sample_queue)     
        #test func to activate mouth. Should activate, then auto deactivate
        self.mouth.active = not self.mouth.active 

    def speak_text(self, text):
        pass

    def queue_syllables(self, syllables=[]):
        self.syllable_queue.append(syllables)

    def update(self,dt):
        #whatever I need it to do
        self.mouth.update(dt)

    def stfu(self):
        self.syllable_queue = []
        self.mouth.active = False