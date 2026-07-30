import random
from . import config
from .units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, ReconOperator, FPVOperator, FPVDrone, SupplyCache


class StrategicAI:
    """
    Стратегический ИИ противника с фазами:
    1. Разведка (первые ходы)
    2. Понимание логистики игрока
    3. Уничтожение складов/погребов
    4. Атака техники
    """
    
    PHASE_RECON = 0
    PHASE_LOGISTICS = 1
    PHASE_ATTACK = 2
    
    def __init__(self, game):
        self.game = game
        self.turn_count = 0
        self.phase = self.PHASE_RECON
        self.recon_turns = 8  # Ходов на разведку
        self.logistics_turns = 15  # Ходов на понимание логистики
        self.known_player_structures = []  # Известные склады/погреба игрока
        self.random_factor = 0.2  # 20% случайности в решениях
        self.drone_targets = {}  # id(drone) -> (tx, ty) патрульная цель
        self.drone_hover = {}  # id(drone) -> unit на котором зависает
        self.drone_returning = {}  # id(drone) -> True дрон возвращается на базу
        
    def get_state(self):
        """Получить текущее состояние карты для принятия решений"""
        return {
            'turn': self.turn_count,
            'phase': self.phase,
            'enemy_units': self._get_enemy_units(),
            'player_units': self._get_visible_player_units(),
            'enemy_structures': self._get_enemy_structures(),
            'known_player_structures': self.known_player_structures,
        }
    
    def decide_actions(self):
        """Принять решения на основе текущего состояния"""
        state = self.get_state()
        actions = []
        
        # Обновление фазы
        if self.turn_count < self.recon_turns:
            self.phase = self.PHASE_RECON
        elif self.turn_count < self.recon_turns + self.logistics_turns:
            self.phase = self.PHASE_LOGISTICS
        else:
            self.phase = self.PHASE_ATTACK
        
        # Разведка
        if self.phase == self.PHASE_RECON:
            actions.extend(self._recon_actions(state))
        
        # Понимание логистики
        if self.phase == self.PHASE_LOGISTICS:
            actions.extend(self._logistics_actions(state))
        
        # Атака
        if self.phase == self.PHASE_ATTACK:
            actions.extend(self._attack_actions(state))
        
        # Общие действия для всех фаз
        actions.extend(self._common_actions(state))
        
        return actions
    
    def _recon_actions(self, state):
        """Действия в фазе разведки"""
        actions = []
        
        # Запуск разведдронов
        if self.turn_count % 3 == 0:
            actions.append({'type': 'deploy_recon'})
        
        # Окапывание пехоты
        if self.turn_count % 4 == 0:
            actions.append({'type': 'entrench'})
        
        # Строительство погребов
        if self.turn_count % 6 == 0:
            actions.append({'type': 'build_cache'})
        
        return actions
    
    def _logistics_actions(self, state):
        """Действия в фазе понимания логистики"""
        actions = []
        
        # Обновление известных структур игрока
        self._update_known_structures(state)
        
        # Продолжение разведки
        if self.turn_count % 4 == 0:
            actions.append({'type': 'deploy_recon'})
        
        # Строительство погребов ближе к игроку
        if self.turn_count % 5 == 0:
            actions.append({'type': 'build_cache_forward'})
        
        # Окапывание
        if self.turn_count % 3 == 0:
            actions.append({'type': 'entrench'})
        
        return actions
    
    def _attack_actions(self, state):
        """Действия в фазе атаки"""
        actions = []
        
        # Обновление известных структур
        self._update_known_structures(state)
        
        # Атака известных складов/погребов
        if self.known_player_structures:
            actions.append({'type': 'attack_structures'})
        
        # Постановка цели для артиллерии
        actions.append({'type': 'artillery_target'})
        
        # Продолжение разведки
        if self.turn_count % 6 == 0:
            actions.append({'type': 'deploy_recon'})
        
        return actions
    
    def _common_actions(self, state):
        """Общие действия для всех фаз"""
        actions = []
        
        # Проверка угрозы от игрока
        if self._player_advancing(state):
            actions.append({'type': 'hide_and_entrench'})
        
        # Случайные действия (симулятор рандома)
        if random.random() < self.random_factor:
            if random.random() < 0.3:
                actions.append({'type': 'random_move'})
        
        return actions
    
    def _get_enemy_units(self):
        """Получить свои юниты"""
        return [u for u in self.game.all_units 
                if u.faction == config.ENEMY and u.is_alive 
                and not isinstance(u, (SupplyTruck, Warehouse))]
    
    def _get_visible_player_units(self):
        """Получить видимые юниты игрока"""
        visible = []
        for unit in self.game.all_units:
            if unit.faction != config.PLAYER or not unit.is_alive:
                continue
            cell = self.game.map.get_cell(unit.x, unit.y)
            if cell and cell.visible:
                visible.append(unit)
        return visible
    
    def _get_enemy_structures(self):
        """Получить свои структуры"""
        return [u for u in self.game.all_units 
                if u.faction == config.ENEMY and u.is_alive 
                and isinstance(u, (Warehouse, SupplyCache))]
    
    def _update_known_structures(self, state):
        """Обновить известные структуры игрока"""
        for unit in state['player_units']:
            if isinstance(unit, (Warehouse, SupplyCache)):
                if unit not in self.known_player_structures:
                    self.known_player_structures.append(unit)
    
    def _player_advancing(self, state):
        """Проверить, продвигается ли игрок вперед"""
        if not state['player_units']:
            return False
        
        # Подсчет юнитов игрока в передней линии
        enemy_warehouse = [u for u in self.game.all_units 
                          if isinstance(u, Warehouse) and u.faction == config.ENEMY and u.is_alive]
        if not enemy_warehouse:
            return False
        
        wh = enemy_warehouse[0]
        advancing_count = 0
        for unit in state['player_units']:
            if isinstance(unit, (Infantry, Tank)):
                dist = abs(unit.x - wh.x) + abs(unit.y - wh.y)
                if dist < 15:  # Игрок близко
                    advancing_count += 1
        
        return advancing_count >= 3
    
    def execute_actions(self, actions):
        """Выполнить принятые решения"""
        self.cleanup_drone_state()
        
        for action in actions:
            if action['type'] == 'deploy_recon':
                self._execute_deploy_recon()
            elif action['type'] == 'entrench':
                self._execute_entrench()
            elif action['type'] == 'build_cache':
                self._execute_build_cache()
            elif action['type'] == 'build_cache_forward':
                self._execute_build_cache_forward()
            elif action['type'] == 'attack_structures':
                self._execute_attack_structures()
            elif action['type'] == 'hide_and_entrench':
                self._execute_hide_and_entrench()
            elif action['type'] == 'random_move':
                self._execute_random_move()
            elif action['type'] == 'artillery_target':
                self._execute_artillery_target()
        
        self._manage_drones()
    
    def _execute_deploy_recon(self):
        """Запустить разведдрон"""
        enemy_warehouses = [u for u in self.game.all_units 
                           if isinstance(u, Warehouse) and u.faction == config.ENEMY and u.is_alive]
        if not enemy_warehouses:
            return
        
        wh = enemy_warehouses[0]
        if wh.batteries < 5:
            return
        
        existing_drones = [u for u in self.game.all_units 
                          if isinstance(u, ReconDrone) and u.faction == config.ENEMY and u.is_alive]
        if len(existing_drones) >= 3:
            return
        
        player_base = self._get_player_base()
        
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = wh.x + dx, wh.y + dy
            cell = self.game.map.get_cell(nx, ny)
            if cell and cell.is_walkable and not self._is_occupied(nx, ny):
                drone = ReconDrone(nx, ny, config.ENEMY, "Вражеский дрон")
                self.game.all_units.append(drone)
                self.game.enemy_units.append(drone)
                self.game.map.add_unit(drone, nx, ny)
                wh.batteries -= 5
                if player_base and self.turn_count >= 10:
                    patrol_x = player_base.x + random.randint(-5, 5)
                    patrol_y = player_base.y + random.randint(-5, 5)
                    patrol_x = max(0, min(self.game.map.width - 1, patrol_x))
                    patrol_y = max(0, min(self.game.map.height - 1, patrol_y))
                    self.drone_targets[id(drone)] = (patrol_x, patrol_y)
                break
    
    def _execute_entrench(self):
        """Окопать пехоту"""
        enemy_infantry = [u for u in self.game.all_units 
                         if isinstance(u, Infantry) and u.faction == config.ENEMY 
                         and u.is_alive and not u.entrenching and not u.building_cache]
        
        for inf in enemy_infantry[:2]:
            cell = self.game.map.get_cell(inf.x, inf.y)
            if cell.entrenchment < inf.max_entrenchment:
                inf.entrenching = True
    
    def _execute_build_cache(self):
        """Построить погреб"""
        enemy_infantry = [u for u in self.game.all_units 
                         if isinstance(u, Infantry) and u.faction == config.ENEMY 
                         and u.is_alive and not u.building_cache]
        if not enemy_infantry:
            return
        
        existing_caches = [u for u in self.game.all_units 
                          if isinstance(u, SupplyCache) and u.faction == config.ENEMY and u.is_alive]
        if len(existing_caches) >= 1:  # ИИ строит только один погреб
            return
        
        for inf in enemy_infantry[:1]:
            cache = SupplyCache(inf.x, inf.y, config.ENEMY, "Вражеский погреб")
            inf.building_cache = cache
            self.game.all_units.append(cache)
            self.game.enemy_units.append(cache)
            self.game.map.add_unit(cache, cache.x, cache.y)
            break
    
    def _execute_build_cache_forward(self):
        """Построить погреб ближе к игроку"""
        enemy_infantry = [u for u in self.game.all_units 
                         if isinstance(u, Infantry) and u.faction == config.ENEMY 
                         and u.is_alive and not u.building_cache]
        if not enemy_infantry:
            return
        
        # Найти пехоту ближе всего к игроку
        player_units = self._get_visible_player_units()
        if not player_units:
            return
        
        best_inf = None
        best_dist = 999
        for inf in enemy_infantry:
            for pu in player_units:
                dist = abs(inf.x - pu.x) + abs(inf.y - pu.y)
                if dist < best_dist:
                    best_dist = dist
                    best_inf = inf
        
        if best_inf and best_dist < 20:
            cache = SupplyCache(best_inf.x, best_inf.y, config.ENEMY, "Передовой погреб")
            best_inf.building_cache = cache
            self.game.all_units.append(cache)
            self.game.enemy_units.append(cache)
            self.game.map.add_unit(cache, cache.x, cache.y)
    
    def _execute_launch_fpv(self):
        """Запустить FPV"""
        enemy_operators = [u for u in self.game.all_units 
                          if isinstance(u, FPVOperator) and u.faction == config.ENEMY and u.is_alive]
        if not enemy_operators:
            return
        
        op = enemy_operators[0]
        if op.fpv_stock <= 0:
            return
        
        enemy_drones = [u for u in self.game.all_units 
                       if isinstance(u, ReconDrone) and u.faction == config.ENEMY and u.is_alive]
        
        priority_target = None
        fallback_target = None

        for unit in self.game.all_units:
            if unit.faction != config.PLAYER or not unit.is_alive:
                continue
            if isinstance(unit, (ReconDrone, FPVDrone)):
                continue
            cell = self.game.map.get_cell(unit.x, unit.y)
            if not cell:
                continue
            dist_to_op = abs(unit.x - op.x) + abs(unit.y - op.y)
            if dist_to_op > config.FPV_OPERATOR_RANGE:
                continue

            spotted_by_drone = False
            for drone in enemy_drones:
                dist = abs(unit.x - drone.x) + abs(unit.y - drone.y)
                if dist <= drone.vision_range:
                    stealth = self.game.map._get_stealth(unit, self.game.map) + self.game.map._cell_stealth_bonus(cell.terrain)
                    detect_range = max(0, drone.vision_range - stealth)
                    if dist <= detect_range:
                        spotted_by_drone = True
                        break
            if spotted_by_drone:
                priority_target = unit
                break

            if not fallback_target:
                spotted_by_unit = False
                for fu in self.game.enemy_units:
                    if not fu.is_alive or fu is op:
                        continue
                    if isinstance(fu, (Warehouse, SupplyCache)):
                        continue
                    fdist = abs(unit.x - fu.x) + abs(unit.y - fu.y)
                    if fdist <= fu.vision_range:
                        spotted_by_unit = True
                        break
                if spotted_by_unit:
                    fallback_target = unit

        target = priority_target or fallback_target
        if not target:
            return
        
        if not op.launch_fpv():
            return
        
        fpv_drone = FPVDrone(op.x, op.y, config.ENEMY, target, f"Вражеский FPV", operator=op)
        self.game.all_units.append(fpv_drone)
        self.game.enemy_units.append(fpv_drone)
        self.game.map.add_unit(fpv_drone, op.x, op.y)
        self.game.fpv_drones_in_flight.append(fpv_drone)
    
    def _execute_artillery_target(self):
        """Поставить цель для вражеской артиллерии"""
        from .units import Artillery
        enemy_artillery = [u for u in self.game.all_units
                          if isinstance(u, Artillery) and u.faction == config.ENEMY and u.is_alive]
        if not enemy_artillery:
            return
        for art in enemy_artillery:
            if art.pending_target:
                continue
            if art.ammo <= 0:
                continue
            best = None
            best_val = -1
            for u in self.game.all_units:
                if u.faction != config.PLAYER or not u.is_alive:
                    continue
                if hasattr(u, 'is_flying') and u.is_flying:
                    continue
                dist = abs(art.x - u.x) + abs(art.y - u.y)
                if dist > config.ARTILLERY_BARRAGE_RANGE:
                    continue
                spotted = False
                for fu in self.game.enemy_units:
                    if not fu.is_alive:
                        continue
                    if isinstance(fu, (Warehouse, SupplyCache)):
                        continue
                    fdist = abs(u.x - fu.x) + abs(u.y - fu.y)
                    if fdist <= fu.vision_range:
                        spotted = True
                        break
                if not spotted:
                    continue
                val = 0
                if isinstance(u, Warehouse):
                    val = 10
                elif isinstance(u, SupplyCache):
                    val = 8
                elif isinstance(u, Tank):
                    val = 6
                elif isinstance(u, Infantry):
                    val = 4
                elif isinstance(u, Artillery):
                    val = 5
                if val > best_val:
                    best_val = val
                    best = u
            if best:
                art.pending_target = (best.x, best.y)

    def _execute_attack_structures(self):
        """Атаковать известные структуры игрока"""
        if not self.known_player_structures:
            return
        
        enemy_combat = [u for u in self.game.all_units 
                       if u.faction == config.ENEMY and u.is_alive 
                       and isinstance(u, (Infantry, Tank))]
        
        for unit in enemy_combat:
            if unit.moved:
                continue
            
            # Найти ближайшую структуру
            best_struct = None
            best_dist = 999
            for struct in self.known_player_structures:
                if not struct.is_alive:
                    continue
                dist = abs(unit.x - struct.x) + abs(unit.y - struct.y)
                if dist < best_dist:
                    best_dist = dist
                    best_struct = struct
            
            if not best_struct:
                continue
            
            # Атаковать если близко
            attack_range = 2 if isinstance(unit, Tank) else 1
            if best_dist <= attack_range and unit.ammo > 0:
                result = self.game.resolve_attack(unit, best_struct)
                if result:
                    if not best_struct.is_alive:
                        self.known_player_structures.remove(best_struct)
                    break
            
            # Двигаться к структуре
            if not unit.moved:
                path = self.game.map.find_path(unit.x, unit.y, best_struct.x, best_struct.y, avoid_occupied=True)
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
                        if isinstance(unit, Infantry):
                            unit.entrenching = False
                        if hasattr(unit, 'fuel'):
                            unit.fuel -= 1
    
    def _execute_hide_and_entrench(self):
        """Спрятаться и окопаться при угрозе"""
        enemy_units = self._get_enemy_units()
        
        for unit in enemy_units:
            if unit.moved:
                continue
            
            if isinstance(unit, (Infantry, FPVOperator, ReconOperator)):
                # Найти ближайший лес или город
                best_cell = None
                best_dist = 999
                for dx in range(-5, 6):
                    for dy in range(-5, 6):
                        nx, ny = unit.x + dx, unit.y + dy
                        cell = self.game.map.get_cell(nx, ny)
                        if not cell or not cell.is_walkable:
                            continue
                        if cell.terrain not in [config.FOREST, config.CITY]:
                            continue
                        if self._is_occupied(nx, ny):
                            continue
                        dist = abs(dx) + abs(dy)
                        if dist < best_dist:
                            best_dist = dist
                            best_cell = (nx, ny)
                
                if best_cell:
                    # Двигаться к укрытию
                    path = self.game.map.find_path(unit.x, unit.y, best_cell[0], best_cell[1], avoid_occupied=True)
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
                
                # Окопаться если в укрытии
                if isinstance(unit, Infantry) and not unit.entrenching:
                    cell = self.game.map.get_cell(unit.x, unit.y)
                    if cell and cell.terrain in [config.FOREST, config.CITY]:
                        if cell.entrenchment < unit.max_entrenchment:
                            unit.entrenching = True
    
    def _execute_random_move(self):
        """Случайное движение (симулятор рандома)"""
        enemy_infantry = [u for u in self.game.all_units 
                         if isinstance(u, Infantry) and u.faction == config.ENEMY 
                         and u.is_alive and not u.moved]
        if not enemy_infantry:
            return
        
        unit = random.choice(enemy_infantry)
        directions = [(-1,0), (1,0), (0,-1), (0,1)]
        random.shuffle(directions)
        
        for dx, dy in directions:
            nx, ny = unit.x + dx, unit.y + dy
            cell = self.game.map.get_cell(nx, ny)
            if cell and cell.is_walkable and not self._is_occupied(nx, ny):
                self.game.map.remove_unit(unit)
                unit.x, unit.y = nx, ny
                self.game.map.add_unit(unit, nx, ny)
                unit.moved = True
                if hasattr(unit, 'fuel'):
                    unit.fuel -= 1
                break

    def _get_player_base(self):
        """Получить базу (склад) игрока"""
        for u in self.game.all_units:
            if isinstance(u, Warehouse) and u.faction == config.PLAYER and u.is_alive:
                return u
        return None

    def _get_enemy_warehouse(self):
        """Получить свой склад"""
        for u in self.game.all_units:
            if isinstance(u, Warehouse) and u.faction == config.ENEMY and u.is_alive:
                return u
        return None

    def _get_enemy_drones(self):
        """Получить свои разведдроны"""
        return [u for u in self.game.all_units
                if isinstance(u, ReconDrone) and u.faction == config.ENEMY and u.is_alive]

    def _move_drone_toward(self, drone, tx, ty, steps=5):
        """Двигать дрон к точке (tx, ty) на steps шагов"""
        for _ in range(steps):
            dx = 0
            if tx > drone.x:
                dx = 1
            elif tx < drone.x:
                dx = -1
            dy = 0
            if ty > drone.y:
                dy = 1
            elif ty < drone.y:
                dy = -1

            nx, ny = drone.x + dx, drone.y + dy
            if nx == drone.x and ny == drone.y:
                break
            nx = max(0, min(self.game.map.width - 1, nx))
            ny = max(0, min(self.game.map.height - 1, ny))

            self.game.map.remove_unit(drone)
            drone.x, drone.y = nx, ny
            self.game.map.add_unit(drone, nx, ny)

    def _manage_drones(self):
        """Управление разведдронами: разведка базы игрока, патрулирование, зависание над целью, возврат при низком заряде"""
        if self.turn_count < 10:
            return
        drones = self._get_enemy_drones()
        if not drones:
            return

        player_base = self._get_player_base()
        own_base = self._get_enemy_warehouse()

        for drone in drones:
            drone_id = id(drone)

            if drone.battery <= config.DRONE_LOW_BATTERY_THRESHOLD:
                if own_base:
                    self.drone_returning[drone_id] = True
                    self.drone_hover.pop(drone_id, None)
                    dist_to_base = abs(drone.x - own_base.x) + abs(drone.y - own_base.y)
                    if dist_to_base <= 1:
                        self.drone_returning.pop(drone_id, None)
                        self.drone_targets.pop(drone_id, None)
                    else:
                        self._move_drone_toward(drone, own_base.x, own_base.y)
                else:
                    self.drone_targets.pop(drone_id, None)
                    self.drone_hover.pop(drone_id, None)
                    self.drone_returning.pop(drone_id, None)
                continue

            self.drone_returning.pop(drone_id, None)

            if drone_id in self.drone_hover:
                hover_target = self.drone_hover[drone_id]
                if hover_target and hover_target.is_alive:
                    dist = abs(drone.x - hover_target.x) + abs(drone.y - hover_target.y)
                    if dist > 1:
                        self._move_drone_toward(drone, hover_target.x, hover_target.y)
                    continue
                else:
                    self.drone_hover.pop(drone_id, None)

            spotted_enemy = None
            for unit in self.game.all_units:
                if unit.faction != config.PLAYER or not unit.is_alive:
                    continue
                if isinstance(unit, (ReconDrone,)):
                    continue
                dist = abs(drone.x - unit.x) + abs(drone.y - unit.y)
                if dist <= drone.vision_range:
                    cell = self.game.map.get_cell(unit.x, unit.y)
                    if cell:
                        stealth = self.game.map._get_stealth(unit, self.game.map) + self.game.map._cell_stealth_bonus(cell.terrain)
                        detect_range = max(0, drone.vision_range - stealth)
                        if dist <= detect_range:
                            spotted_enemy = unit
                            break

            if spotted_enemy:
                self.drone_hover[drone_id] = spotted_enemy
                self.drone_targets.pop(drone_id, None)
                dist = abs(drone.x - spotted_enemy.x) + abs(drone.y - spotted_enemy.y)
                if dist > 1:
                    self._move_drone_toward(drone, spotted_enemy.x, spotted_enemy.y)
                continue

            if drone_id not in self.drone_targets:
                if player_base:
                    patrol_x = player_base.x + random.randint(-5, 5)
                    patrol_y = player_base.y + random.randint(-5, 5)
                    patrol_x = max(0, min(self.game.map.width - 1, patrol_x))
                    patrol_y = max(0, min(self.game.map.height - 1, patrol_y))
                    self.drone_targets[drone_id] = (patrol_x, patrol_y)
                else:
                    patrol_x = random.randint(0, self.game.map.width - 1)
                    patrol_y = random.randint(0, self.game.map.height - 1)
                    self.drone_targets[drone_id] = (patrol_x, patrol_y)

            target = self.drone_targets[drone_id]
            dist_to_target = abs(drone.x - target[0]) + abs(drone.y - target[1])

            if dist_to_target <= 1:
                if player_base:
                    patrol_x = player_base.x + random.randint(-8, 8)
                    patrol_y = player_base.y + random.randint(-8, 8)
                    patrol_x = max(0, min(self.game.map.width - 1, patrol_x))
                    patrol_y = max(0, min(self.game.map.height - 1, patrol_y))
                    self.drone_targets[drone_id] = (patrol_x, patrol_y)
                else:
                    patrol_x = random.randint(0, self.game.map.width - 1)
                    patrol_y = random.randint(0, self.game.map.height - 1)
                    self.drone_targets[drone_id] = (patrol_x, patrol_y)
            else:
                self._move_drone_toward(drone, target[0], target[1])

    def cleanup_drone_state(self):
        """Очистить состояние для уничтоженных дронов"""
        alive_ids = {id(u) for u in self.game.all_units
                     if isinstance(u, ReconDrone) and u.faction == config.ENEMY and u.is_alive}
        for d in list(self.drone_targets):
            if d not in alive_ids:
                del self.drone_targets[d]
        for d in list(self.drone_hover):
            if d not in alive_ids:
                del self.drone_hover[d]
        for d in list(self.drone_returning):
            if d not in alive_ids:
                del self.drone_returning[d]
    
    def _is_occupied(self, x, y, exclude=None):
        """Проверить занята ли клетка"""
        for u in self.game.all_units:
            if u is exclude:
                continue
            if u.x == x and u.y == y and u.is_alive:
                return True
        return False
