from Renderer import Renderer 
from FaceScene import FaceObject,Transform
import pygame

ren = Renderer(
    [1080, 1080],
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
                shape_state= 'Circle',
                vert_count= 100,
                init_transform=Transform(origin_position=[540,540], scale=100)
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
        pygame.display.flip()



main_loop(1)