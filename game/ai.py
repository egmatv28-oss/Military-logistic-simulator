from . import config
from .units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, ReconOperator, FPVOperator, FPVDrone, SupplyCache
from .strategic_ai import StrategicAI


class AIController:
    def __init__(self, game):
        self.game = game
        self.strategic_ai = StrategicAI(game)

    def do_turn(self):
        self.strategic_ai.turn_count += 1
        
        # Получить решения от стратегического ИИ
        actions = self.strategic_ai.decide_actions()
        
        # Выполнить действия
        self.strategic_ai.execute_actions(actions)
        
        # Базовое движение юнитов
        return self._move_combat_units()
    
    def _move_combat_units(self):
        """Движение боевых юнитов к ближайшим целям"""
        results = []
        enemies = [u for u in self.game.all_units 
                  if u.faction == config.ENEMY and u.is_alive 
                  and isinstance(u, (Infantry, Tank))]

        for unit in enemies:
            if not unit.is_alive or unit.moved:
                continue

            # Найти ближайшую цель игрока
            targets = []
            for t in self.game.all_units:
                if t.faction == config.PLAYER and t.is_alive:
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
                    nx, ny = path[1]
                    cell = self.game.map.get_cell(nx, ny)
                    if cell and cell.is_walkable:
                        if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)) and unit.fuel <= 0:
                            continue
                        self.game.map.remove_unit(unit)
                        unit.x, unit.y = nx, ny
                        self.game.map.add_unit(unit, nx, ny)
                        unit.moved = True
                        if hasattr(unit, 'fuel'):
                            unit.fuel -= 1

        return results
