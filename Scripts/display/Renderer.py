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

        self.crt_overlay = pygame.Surface(self.RESOLUTION, pygame.SRCALPHA)

        for y in range(0, self.RESOLUTION[0], 3):
            pygame.draw.line(self.crt_overlay, (0, 0, 0, 45), (0, y), (self.RESOLUTION[0], y))
    
        self.crt_overlay.fill((40, 80, 60, 20), special_flags=pygame.BLEND_RGBA_ADD)

    def apply_crt(self):    
        self.screen.blit(self.crt_overlay, (0, 0))