"""Базовый класс для контроллеров игроков (AI/Человек)"""
from abc import ABC, abstractmethod


class BaseController(ABC):
    """Абстрактный базовый класс для всех контроллеров"""
    
    def __init__(self, game, faction):
        self.game = game
        self.faction = faction  # config.PLAYER или config.ENEMY
    
    @abstractmethod
    def take_turn(self):
        """Выполнить ход. Возвращает список результатов атак."""
        pass
    
    @abstractmethod
    def get_name(self):
        """Вернуть имя контроллера для отображения"""
        pass
    
    def is_ai(self):
        """Является ли этот контроллер AI"""
        return False
    
    def is_human(self):
        """Является ли этот контроллер человеком"""
        return False
