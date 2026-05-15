import pygame

class Button:
    def __init__(self, 
                 rect=[0,0,100,100], 
                 text="None", 
                 on_clicked=None

                 ):
        self.rect = pygame.Rect(rect[0],rect[1],rect[2],rect[3])
        self.text = text
        self.hovered = False
        self.on_clicked = on_clicked

    def update(self, events):
        mouse_pos = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        for event in events:
            if self.clicked(event):
                self.eventOnClicked()

    def draw(self, screen, events):

        color = (180,180,180)
        self.update(events)
        if self.hovered:
            color = (255,255,255)

        pygame.draw.rect(screen, color, self.rect)

    def clicked(self, event):

        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and self.hovered
        )
    
    def eventOnClicked(self):
        if self.on_clicked:
            self.on_clicked()