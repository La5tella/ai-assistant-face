import pygame


class Renderer:

    def __init__(self, windowRes, objectBank, displayType):

        self.RESOLUTION = windowRes
        """
        Sets resolution of the window.
        """

        self.OBJBANK = objectBank
        """
        Holds initialized objects.
        """

        self.DISPLAY = displayType
        """
        pygame.FULLSCREEN, pygame.RESIZABLE, etc.
        """

        pygame.init()

        self.screen = pygame.display.set_mode(
            (self.RESOLUTION[0], self.RESOLUTION[1]),
            self.DISPLAY
        )

        self.clock = pygame.time.Clock()

        self.running = True

    def main_loop(self):

        while self.running:

            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    self.running = False

            self.screen.fill((0, 0, 0))

            pygame.draw.polygon(
                self.screen,
                (255, 255, 255),
                [(100, 100), (200, 100), (150, 200)]
            )

            pygame.display.flip()


renderer = Renderer(
    [1080, 1080],
    None,
    pygame.RESIZABLE
)

renderer.main_loop()