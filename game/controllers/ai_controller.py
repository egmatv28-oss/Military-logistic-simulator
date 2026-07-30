"""AI контроллер - использует стратегический AI"""
from .. import config
from ..units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, ReconOperator, FPVOperator, FPVDrone, SupplyCache
from ..strategic_ai import StrategicAI
from .base_controller import BaseController


class AIController(BaseController):
    """Контроллер для AI игрока"""
    
    def __init__(self, game, faction):
        super().__init__(game, faction)
        self.strategic_ai = StrategicAI(game)
    
    def take_turn(self):
        """Выполнить ход AI"""
        self.strategic_ai.turn_count += 1
        
        # Получить решения от стратегического AI
        actions = self.strategic_ai.decide_actions()
        
        # Выполнить действия
        self.strategic_ai.execute_actions(actions)
        
        # Движение боевых юнитов
        return self._move_combat_units()
    
    def get_name(self):
        return "AI"
    
    def is_ai(self):
        return True
    
    def _move_combat_units(self):
        """Движение боевых юнитов к ближайшим целям"""
        results = []
        
        # Определяем свои и вражеские фракции
        my_faction = self.faction
        enemy_faction = config.ENEMY if my_faction == config.PLAYER else config.PLAYER
        
        enemies = [u for u in self.game.all_units 
                  if u.faction == my_faction and u.is_alive 
                  and isinstance(u, (Infantry, Tank))]

        for unit in enemies:
            if not unit.is_alive or unit.moved:
                continue

            # Найти ближайшую цель противника
            targets = []
            for t in self.game.all_units:
                if t.faction == enemy_faction and t.is_alive:
                    if isinstance(t, (ReconDrone, ReconOperator, FPVOperator, FPVDrone)):
                        continue
                    priority = 0
                    if isinstance(t, Warehouse):
                        priority = 3
                    elif isinstance(t, SupplyTruck):
                        priority = 2
                    elif isinstance(t, SupplyCache):
                        priority = 1
                    dist = self.game.map.distance(unit.x, unit.y, t.x, t.y)
                    targets.append((t, dist - priority * 3))
            
            if not targets:
                continue

            closest = min(targets, key=lambda x: x[1])[0]
            dist = self.game.map.distance(unit.x, unit.y, closest.x, closest.y)

            # Атаковать если в радиусе
            attack_range = 2 if isinstance(unit, Tank) else 1
            if dist <= attack_range and unit.ammo > 0:
                result = self.game.resolve_attack(unit, closest)
                if result:
                    results.append(result)
                continue

            # Двигаться к цели если не двигался
            if not unit.moved:
                path = self.game.map.find_path(unit.x, unit.y, closest.x, closest.y, avoid_occupied=True)
                if path and len(path) > 1:
                    # ИИ предпочитает лес и город, избегает открытых полей
                    best_move = None
                    best_score = -999
                    
                    for nx, ny in path[1:3]:  # Проверяем первые 2 шага
                        cell = self.game.map.get_cell(nx, ny)
                        if not cell or not cell.is_walkable:
                            continue
                        
                        # Оценка местности
                        score = 0
                        if cell.terrain == config.FOREST:
                            score = 10  # Лес - хорошо
                        elif cell.terrain == config.CITY:
                            score = 8   # Город - хорошо
                        elif cell.terrain == config.ROAD:
                            score = 5   # Дорога - нормально
                        elif cell.terrain == config.FIELD:
                            score = -5  # Поле - плохо
                        
                        # Бонус за близость к цели
                        dist_to_target = self.game.map.distance(nx, ny, closest.x, closest.y)
                        score += (10 - dist_to_target)
                        
                        if score > best_score:
                            best_score = score
                            best_move = (nx, ny)
                    
                    if best_move:
                        nx, ny = best_move
                        if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)) and unit.fuel <= 0:
                            continue
                        self.game.map.remove_unit(unit)
                        unit.x, unit.y = nx, ny
                        self.game.map.add_unit(unit, nx, ny)
                        unit.moved = True
                        if hasattr(unit, 'fuel'):
                            unit.fuel -= 1

        return results
