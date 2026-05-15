from Renderer import Renderer 
from FaceScene import FaceObject,Transform
from UI import Button
import pygame

RESOLUTION = [720,720]

ren = Renderer(
    RESOLUTION,
    None,
    pygame.RESIZABLE
)

objPool = []


def cycle_all_shape_states():
    for obj in objPool:
        obj.cycle_shape_state()
        

def main_loop(objCount):
    running = True

    debug_button = Button(
        rect = [10,10,100,100],
        text = "Cycle State",
        on_clicked = lambda: cycle_all_shape_states()
    )

    for i in range(objCount):
        objPool.append(
            FaceObject(
                object_id= i,
                layer= 0,
                shape_state= 'Circle',
                aspect_ratio=[16,9],
                vert_count= 32,
                init_transform=Transform(origin_position=[RESOLUTION[0]/2,RESOLUTION[1]/2], scale=100),
                vert_debug=True
            )
        )

    while running:
        dt = ren.clock.tick(60) / 1000.0
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
        ren.screen.fill((0, 0, 0))
        for obj in objPool:
            if obj.active:
                obj.update_shape_state("linear",dt)
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
           debug_button.draw(ren.screen,events)

        pygame.display.flip()



main_loop(1)