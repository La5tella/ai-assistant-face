from Renderer import Renderer 
from FaceScene import FaceObject, FaceScene, Transform
from UI import Button
import pygame
import json
from pathlib import Path
import queue
from Listener import start_listener, drain_commands, start_debug_sender


BASE_DIR = Path(__file__).resolve().parent
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
    debug_button_2 = Button(
        rect = [10,90,75,25],
        text = "Start Debug sender",
        on_clicked=lambda: start_debug_sender(),
        screen=ren,
        font = pygame.font.SysFont('Helvetica',size=14,bold=True)
    )
    debug_buttons = [debug_button, debug_button_1, debug_button_2]

    face_scene = FaceScene(anim_library=anim_library, expression_data=expression_data, objCount=objCount, RESOLUTION=RESOLUTION)
    face_scene.set_expression(expression_data["default_state"], duration=0)

    command_queue = queue.Queue()
    listener = start_listener(command_queue)

    while running:
        dt = ren.clock.tick(60) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        ren.screen.fill((0, 0, 0))
        listen_for_input(command_queue)
        face_scene.update(dt)
        for drawables in face_scene.drawables:
            
            pygame.draw.polygon(
                ren.screen,
                drawables.color,
                drawables.verts
            )
            if drawables.debug:
                face_scene.objects[drawables.id].draw_vert_debug(screen=ren)

        for button in debug_buttons:
           button.draw(events)

        ren.apply_crt()
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
        if command["type"] == "expression":
            face_scene.set_expression(command.get("name", "neutral"))

        elif command["type"] == "speak":
            syllables = [
                {"syllable": name, "time": duration}
                for name, duration in command.get("syllables", [])
            ]
            face_scene.mouth_manager.activate_speak(syllables)

        elif command["type"] == "stop_speech":
            face_scene.mouth_manager.stfu()


if __name__ == "__main__":
    main_loop(5)

