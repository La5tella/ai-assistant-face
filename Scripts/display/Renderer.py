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

        for y in range(0, self.RESOLUTION[1], 3):
            pygame.draw.line(self.crt_overlay, (0, 0, 0, 45), (0, y), (self.RESOLUTION[0], y))
    
        self.crt_overlay.fill((40, 80, 60, 20), special_flags=pygame.BLEND_RGBA_ADD)

    def draw_drawables(self, drawable):
        
        pygame.draw.polygon(
                self.screen,
                drawable.color,
                drawable.verts
            )

    def post_processing(self):
        base_frame = self.screen.copy()

        self.pixelate()
        #self.glow(base_frame)
        #self.restore_color(base_frame, (113, 255, 236))
        self.apply_crt()

        

    def apply_crt(self):    
        self.screen.blit(self.crt_overlay, (0, 0))

    def pixelate(self):
        low_resolution = (
            max(1, self.RESOLUTION[0] // 3),
            max(1, self.RESOLUTION[1] // 3)
        )
        pixel_surface = pygame.transform.scale(self.screen, low_resolution)
        pygame.transform.scale(pixel_surface, self.RESOLUTION, self.screen)
    
    def glow(self, source_surface):
        glow_surface = source_surface.copy()
        low_resolution = (
            max(1, self.RESOLUTION[0] // 6),
            max(1, self.RESOLUTION[1] // 6)
        )

        glow_surface.fill((90, 230, 220, 255), special_flags=pygame.BLEND_RGBA_MULT)
        glow_surface = pygame.transform.smoothscale(glow_surface, low_resolution)
        glow_surface = pygame.transform.smoothscale(glow_surface, self.RESOLUTION)
        glow_surface.set_alpha(180)

        self.screen.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.screen.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def restore_color(self, source_surface, color, tolerance=8):
        color_mask = pygame.mask.from_threshold(
            source_surface,
            color,
            (tolerance, tolerance, tolerance, 255)
        )
        restore_surface = pygame.Surface(self.RESOLUTION, pygame.SRCALPHA)
        color_mask.to_surface(
            restore_surface,
            setcolor=(*color, 255),
            unsetcolor=(0, 0, 0, 0)
        )

        self.screen.blit(restore_surface, (0, 0))
        