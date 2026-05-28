from Renderer import Renderer 
from FaceScene import FaceObject, FaceScene, Transform
from UI import Button
import pygame
import json
from pathlib import Path
import math


BASE_DIR = Path(__file__).resolve().parent
RESOLUTION = [720,720]

ren = Renderer(
    RESOLUTION,
    None,
    pygame.RESIZABLE
)

objPool = []
face_scene = None

with open(BASE_DIR / "dataLibrary/expressions.json", "r") as file:
    expression_data = json.load(file)
with open(BASE_DIR / "dataLibrary/anims.json", "r") as file:
    anim_library = json.load(file)

def cycle_all_shape_states():
    for obj in objPool:
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


    for i in range(objCount):
        objPool.append(
            FaceObject(
                object_id= i,
                layer= 0,
                shape_state= 'Circle',
                aspect_ratio=[16,9],
                anim_dict=anim_library,
                vert_count= 32,
                init_transform=Transform(origin_position=[(RESOLUTION[0]/4)+(i*(RESOLUTION[0]/2)),RESOLUTION[1]/2], scale=100),
                vert_debug=True,
                active=False
            )
        )
    
    face_scene = FaceScene(objPool, expression_data)
    face_scene.set_expression(expression_data["default_state"], duration=0)

    while running:
        dt = ren.clock.tick(60) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        ren.screen.fill((0, 0, 0))
        face_scene.update(dt)
        for obj in objPool:
            if obj.active:
                points = [vert.position for vert in obj.verts]
                pygame.draw.polygon(
                    ren.screen,
                    obj.color,
                    points
                )
                if obj.vert_debug:
                    for i, vert in enumerate(obj.verts):
                        vert.draw_vert_debug(vertId=i,screen=ren)
        if debug_button != None:
           debug_button.draw(events)

        pygame.display.flip()


def apply_face_state():
    if face_scene is not None:
        face_scene.set_expression(expression_data["default_state"], duration=0)
        return

    default_state_name = expression_data["default_state"]
    default_state = expression_data["states"][default_state_name]

    for obj_id, state_data in default_state.items():
        obj = objPool[int(obj_id)]

        for attr, value in state_data.items():
            if attr == "position":
                obj.transform.origin_position = value
            else:
                setattr(obj, attr, value)

        

if __name__ == "__main__":
    main_loop(5)
