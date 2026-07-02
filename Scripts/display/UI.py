import pygame

class Button:
    def __init__(self, 
                 rect=[0,0,100,100], 
                 text=None, 
                 on_clicked=None,
                 screen=None,
                 font=None,
                 font_color=(0,255,255)
                 ):
        self.rect = pygame.Rect(rect[0],rect[1],rect[2],rect[3])
        self.text = text
        if font:
            screen.fonts.append(font)
            self.font = len(screen.fonts)-1
        else:
            self.font = 0
        self.font_color=font_color 

        self.screen = screen
        self.hovered = False
        self.on_clicked = on_clicked

    def update(self, events):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        for event in events:
            if self.clicked(event):
                self.eventOnClicked()

    def draw(self, events):
        
        color = (180,180,180)
        self.update(events)
        if self.hovered:
            color = (255,255,255)

        pygame.draw.rect(self.screen.screen, color, self.rect)
        if self.screen:
            
            text_surface = self.screen.fonts[self.font].render(self.text, True, self.font_color)
            self.screen.screen.blit(text_surface, [self.rect[0],self.rect[1]])

    def clicked(self, event):

        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and self.hovered
        )
    
    def eventOnClicked(self):
        if self.on_clicked:
            self.on_clicked()