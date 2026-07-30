"""Главное меню игры"""
import pygame
from .. import config
from ..utils.save_load import SaveLoadSystem


class Menu:
    """Главное меню"""
    
    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.SysFont(None, 72)
        self.font_medium = pygame.font.SysFont(None, 48)
        self.font_small = pygame.font.SysFont(None, 36)
        
        self.selected_option = 0
        self.options = [
            ("Новая игра (vs AI)", "new_game_ai"),
            ("Новая игра (vs Игрок)", "new_game_human"),
            ("Загрузить игру", "load_game"),
            ("Настройки", "settings"),
            ("Выход", "quit"),
        ]
        
        self.result = None
        self.game_mode = None
    
    def handle_event(self, event):
        """Обработка событий"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                self.result = self.options[self.selected_option][1]
                return self.result
        
        return None
    
    def draw(self):
        """Отрисовка меню"""
        self.screen.fill((20, 30, 40))
        
        # Заголовок
        title = self.font_large.render("ВОЙНА ЛОГИСТИКИ", True, (200, 220, 255))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)
        
        subtitle = self.font_small.render("Симулятор военного снабжения", True, (150, 170, 200))
        subtitle_rect = subtitle.get_rect(center=(config.SCREEN_WIDTH // 2, 200))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Опции меню
        y_start = 300
        y_spacing = 60
        
        for i, (text, _) in enumerate(self.options):
            color = (255, 255, 100) if i == self.selected_option else (200, 200, 200)
            option_text = self.font_medium.render(text, True, color)
            option_rect = option_text.get_rect(center=(config.SCREEN_WIDTH // 2, y_start + i * y_spacing))
            self.screen.blit(option_text, option_rect)
            
            # Индикатор выбора
            if i == self.selected_option:
                arrow = self.font_medium.render("▶", True, color)
                arrow_rect = arrow.get_rect(right=option_rect.left - 20, centery=option_rect.centery)
                self.screen.blit(arrow, arrow_rect)
        
        # Подсказка
        hint = self.font_small.render("↑↓ - выбор, Enter - подтвердить", True, (100, 120, 150))
        hint_rect = hint.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 50))
        self.screen.blit(hint, hint_rect)
        
        pygame.display.flip()
    
    def get_result(self):
        """Получить результат выбора"""
        return self.result
    
    def reset(self):
        """Сбросить состояние меню"""
        self.selected_option = 0
        self.result = None


class LoadGameMenu:
    """Меню загрузки игры"""
    
    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.SysFont(None, 48)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)
        
        self.saves = SaveLoadSystem.list_saves()
        self.selected_option = 0
        self.result = None
    
    def handle_event(self, event):
        """Обработка событий"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.result = "back"
                return self.result
            elif event.key == pygame.K_UP:
                if self.saves:
                    self.selected_option = (self.selected_option - 1) % len(self.saves)
            elif event.key == pygame.K_DOWN:
                if self.saves:
                    self.selected_option = (self.selected_option + 1) % len(self.saves)
            elif event.key == pygame.K_RETURN:
                if self.saves:
                    self.result = self.saves[self.selected_option]['name']
                    return self.result
            elif event.key == pygame.K_DELETE:
                if self.saves:
                    save_name = self.saves[self.selected_option]['name']
                    SaveLoadSystem.delete_save(save_name)
                    self.saves = SaveLoadSystem.list_saves()
                    if self.selected_option >= len(self.saves):
                        self.selected_option = max(0, len(self.saves) - 1)
        
        return None
    
    def draw(self):
        """Отрисовка меню загрузки"""
        self.screen.fill((20, 30, 40))
        
        # Заголовок
        title = self.font_large.render("ЗАГРУЗИТЬ ИГРУ", True, (200, 220, 255))
        title_rect = title.get_rect(center=(config.SCREEN_WIDTH // 2, 80))
        self.screen.blit(title, title_rect)
        
        if not self.saves:
            no_saves = self.font_medium.render("Нет сохранений", True, (150, 150, 150))
            no_saves_rect = no_saves.get_rect(center=(config.SCREEN_WIDTH // 2, 300))
            self.screen.blit(no_saves, no_saves_rect)
        else:
            y_start = 150
            y_spacing = 50
            
            for i, save in enumerate(self.saves):
                color = (255, 255, 100) if i == self.selected_option else (200, 200, 200)
                
                # Имя сохранения и ход
                text = f"Ход {save['turn']} - {save['timestamp'][:19]}"
                save_text = self.font_medium.render(text, True, color)
                save_rect = save_text.get_rect(center=(config.SCREEN_WIDTH // 2, y_start + i * y_spacing))
                self.screen.blit(save_text, save_rect)
                
                if i == self.selected_option:
                    arrow = self.font_medium.render("▶", True, color)
                    arrow_rect = arrow.get_rect(right=save_rect.left - 20, centery=save_rect.centery)
                    self.screen.blit(arrow, arrow_rect)
        
        # Подсказка
        hint = self.font_small.render("↑↓ - выбор, Enter - загрузить, Delete - удалить, Esc - назад", 
                                      True, (100, 120, 150))
        hint_rect = hint.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 50))
        self.screen.blit(hint, hint_rect)
        
        pygame.display.flip()
    
    def get_result(self):
        """Получить результат выбора"""
        return self.result
