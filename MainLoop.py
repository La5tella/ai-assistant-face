from Renderer import Renderer 
from FaceScene import FaceObject,Transform
import pygame

RESOLUTION = [720,720]

ren = Renderer(
    RESOLUTION,
    None,
    pygame.RESIZABLE
)

objPool = []

def main_loop(objCount):
    running = True

    for i in range(objCount):
        objPool.append(
            FaceObject(
                object_id= i,
                layer= 0,
                shape_state= 'Rectangle',
                aspect_ratio=[9,16],
                vert_count= 20,
                init_transform=Transform(origin_position=[RESOLUTION[0]/2,RESOLUTION[1]/2], scale=10),
                vert_debug=True
            )
        )
    while running:
        dt = ren.clock.tick(60) / 1000.0
        for event in pygame.event.get():
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
        pygame.display.flip()



main_loop(1)