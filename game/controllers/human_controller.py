"""Контроллер для игрока-человека (hot-seat)"""
from .base_controller import BaseController
from .. import config


class HumanController(BaseController):
    """Контроллер для человеческого игрока"""
    
    def __init__(self, game, faction):
        super().__init__(game, faction)
        self.waiting_for_input = False
        self.turn_complete = False
    
    def take_turn(self):
        """
        Для человеческого контроллера этот метод просто помечает начало хода.
        Реальные действия выполняются через UI.
        """
        self.waiting_for_input = True
        self.turn_complete = False
        return []
    
    def get_name(self):
        return f"Игрок ({'Синие' if self.faction == config.PLAYER else 'Красные'})"
    
    def is_human(self):
        return True
    
    def is_my_turn(self):
        """Проверить, сейчас ли ход этого игрока"""
        return self.game.current_player_faction == self.faction
    
    def end_turn(self):
        """Завершить ход"""
        self.turn_complete = True
        self.waiting_for_input = False
