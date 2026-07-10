from Scripts.display.Renderer import Renderer 
from Scripts.display.FaceScene import FaceObject, FaceScene, Transform
from Scripts.display.UI import Button
import pygame
import json
from pathlib import Path
import queue
from Scripts.aiIntegration.CommandListener import start_listener, drain_commands
from Scripts.aiIntegration.AudioPlayer import AudioPlayer


BASE_DIR = Path(__file__).resolve().parents[1]
RESOLUTION = [720,720]

ren = Renderer(
    RESOLUTION,
    None,
    pygame.RESIZABLE
)

face_scene = None

with open(BASE_DIR / "dataLibrary/expressions.json", "r") as file:
    expression_data = json.load(file)
with open(BASE_DIR / "dataLibrary/anims.json", "r") as file:
    anim_library = json.load(file)



def cycle_all_shape_states():
    for obj in face_scene.objects:
        if obj.active:
            obj.cycle_shape_state()
        

def main_loop(objCount):
    global face_scene
    global audio_player

    running = True
    
    debug_button = Button(
        rect = [10,10,75,25],
        text = "Cycle State",
        on_clicked = lambda: cycle_all_shape_states(),
        screen=ren,
        font = pygame.font.SysFont('Helvetica',size=14,bold=True)
    )
    debug_button_1 = Button(
        rect = [10,50,75,25],
        text = "Toggle Mouth",
        on_clicked = lambda: activate_mouth(),
        screen=ren,
        font = pygame.font.SysFont('Helvetica',size=14,bold=True)
    )
    
    debug_buttons = [debug_button, debug_button_1]

    face_scene = FaceScene(anim_library=anim_library, expression_data=expression_data, objCount=objCount, RESOLUTION=RESOLUTION)
    face_scene.set_expression(expression_data["default_state"], duration=0)
    audio_player = AudioPlayer()

    command_queue = queue.Queue()
    listener = start_listener(command_queue)

    while running:
        dt = ren.clock.tick(60) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        
        listen_for_input(command_queue)
        face_scene.update(dt)
        
        ren.screen.fill((0, 0, 0))

        for drawable in face_scene.drawables:
            
            ren.draw_drawables(drawable)
            if drawable.debug:
                face_scene.objects[drawable.id].draw_vert_debug(screen=ren)

        ren.post_processing()
        
        for button in debug_buttons:
           button.draw(events)

        pygame.display.flip()


def apply_face_state():
    if face_scene is not None:
        face_scene.set_expression(expression_data["default_state"], duration=0)
        return

    default_state_name = expression_data["default_state"]
    default_state = expression_data["states"][default_state_name]

    for obj_id, state_data in default_state.items():
        obj = face_scene.objects[int(obj_id)]

        for attr, value in state_data.items():
            if attr == "position":
                obj.transform.origin_position = value
            else:
                setattr(obj, attr, value)
    print("hello")

def activate_mouth():
    face_scene.mouth_manager.activate_speak()      

def listen_for_input(command_queue):
    for command in drain_commands(command_queue):
        
        match command["type"]: 
            case "expression":
                face_scene.set_expression(command.get("name", "neutral"))

            case "speak":
                syllables = [
                    {"syllable": name, "time": duration, "total_time":total_time}
                    for name, duration, total_time in command.get("syllables", [])
                ]
                face_scene.mouth_manager.activate_speak(syllables)

            case "play":
                audio_player.play_base64_audio(command.get("audio", None)) 

            case "stop_speech":
                face_scene.mouth_manager.stfu()
                audio_player.stfu()


if __name__ == "__main__":
    main_loop(5)

