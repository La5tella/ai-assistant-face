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

        self.fonts = [pygame.font.SysFont('Arial', size=14)]

        self.screen = pygame.display.set_mode(
            (self.RESOLUTION[0], self.RESOLUTION[1]),
            self.DISPLAY
        )

        self.clock = pygame.time.Clock()

        self.running = True

    