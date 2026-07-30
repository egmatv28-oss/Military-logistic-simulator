import pygame
from .. import config


class ESPRenderer:
    def __init__(self, renderer):
        self.r = renderer

    def _draw_hotseat_switch(self, game):
        """Отрисовка экрана переключения в hot-seat режиме"""
        # Полупрозрачный фон
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.r.screen.blit(overlay, (0, 0))
        
        # Текст
        font_large = pygame.font.SysFont("consolas", 48)
        font_medium = pygame.font.SysFont("consolas", 32)
        
        if game.current_player_faction == config.PLAYER:
            text = "Ход Игрока 1 (Синие)"
            color = (100, 150, 255)
        else:
            text = "Ход Игрока 2 (Красные)"
            color = (255, 100, 100)
        
        title = font_large.render(text, True, color)
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 50))
        self.r.screen.blit(title, title_rect)
        
        hint = font_medium.render("Передайте компьютер сопернику и нажмите Enter", 
                                  True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 20))
        self.r.screen.blit(hint, hint_rect)

    def _draw_cheat_console(self, game):
        """Отрисовка консоли читов"""
        # Полупрозрачный фон
        overlay = pygame.Surface((config.SCREEN_WIDTH, 60), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.r.screen.blit(overlay, (0, config.SCREEN_HEIGHT - 60))
        
        # Текст
        font = pygame.font.SysFont("consolas", 20)
        prompt = font.render("CHEAT> ", True, (0, 255, 0))
        self.r.screen.blit(prompt, (10, config.SCREEN_HEIGHT - 45))
        
        # Ввод
        input_text = font.render(game.ui.cheat_input, True, (255, 255, 255))
        self.r.screen.blit(input_text, (100, config.SCREEN_HEIGHT - 45))
        
        # Подсказка
        hint = font.render("ESC - закрыть, Enter - выполнить, help - список читов", 
                          True, (150, 150, 150))
        self.r.screen.blit(hint, (10, config.SCREEN_HEIGHT - 25))
