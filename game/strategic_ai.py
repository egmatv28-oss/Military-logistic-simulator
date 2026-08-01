import random
from . import config
from .units import (Infantry, Tank, ReconDrone, SupplyTruck, Warehouse,
                    ReconOperator, FPVOperator, FPVDrone, SupplyCache,
                    Artillery, RadarEW)


class BattleGroup:
    """Боевая группа: пехота, танк, артиллерия, FPV, разведка, грузовик"""

    def __init__(self, group_id):
        self.id = group_id
        self.infantry = []
        self.tank = None
        self.artillery = None
        self.fpv_operator = None
        self.recon_operator = None
        self.truck = None
        self.target_pos = None
        self.cache = None
        self.warehouse = None
        self.formed = False
        self.deployed = False
        self.fortified = False
        self.supply_active = False


class StrategicAI:
    """
    Стратегический ИИ с боевыми группами:
    1. Формирование групп сразу при старте
    2. Развёртывание на позиции (лес/город)
    3. Фортификация: погреб, маршрут снабжения, окопы
    4. Операции: дроны, FPV, наступление при 3x преимуществе
    """

    ADVANTAGE_THRESHOLD = config.AI_ADVANTAGE_THRESHOLD

    def __init__(self, game):
        self.game = game
        self.turn_count = 0
        self.groups = []
        self.known_player_structures = []
        self.known_player_units = []
        self.drone_targets = {}
        self.drone_hover = {}
        self.drone_returning = {}
        self._strategic_points = []
        self._points_assigned = False

    def decide_actions(self):
        actions = []
        if not self.groups:
            actions.append({'type': 'form_group'})
        self._clear_warehouse_area()
        for group in self.groups:
            if not group.deployed:
                actions.append({'type': 'deploy_group', 'group_id': group.id})
                if group.truck and group.truck.is_alive:
                    actions.append({'type': 'run_supply', 'group_id': group.id})
                continue
            if not group.fortified:
                actions.append({'type': 'fortify_group', 'group_id': group.id})
            if group.truck and group.truck.is_alive:
                actions.append({'type': 'run_supply', 'group_id': group.id})
        self._reposition_fpv_operators()
        advantage = self._calc_advantage()
        if advantage >= self.ADVANTAGE_THRESHOLD and self.turn_count > config.AI_OFFENSIVE_MIN_TURN:
            actions.append({'type': 'offensive'})
        else:
            actions.append({'type': 'defensive_ops'})
        if self.turn_count % config.AI_RECON_DEPLOY_INTERVAL == 0:
            actions.append({'type': 'deploy_recon'})
        actions.append({'type': 'artillery_target'})
        return actions

    def execute_actions(self, actions):
        self.cleanup_drone_state()
        self._update_intel()
        handlers = {
            'form_group': self._do_form_group,
            'deploy_group': self._do_deploy_group,
            'fortify_group': self._do_fortify_group,
            'run_supply': self._do_run_supply,
            'offensive': self._do_offensive,
            'defensive_ops': self._do_defensive_ops,
            'deploy_recon': self._do_deploy_recon,
            'artillery_target': self._do_artillery_target,
        }
        for action in actions:
            handler = handlers.get(action.get('type'))
            if handler:
                handler(action)
        self._manage_drones()

    # ── Intel ──────────────────────────────────────────────────────

    def _update_intel(self):
        for u in self.game.all_units:
            if u.faction != config.PLAYER or not u.is_alive:
                continue
            cell = self.game.map.get_cell(u.x, u.y)
            if not cell or not cell.visible:
                continue
            if isinstance(u, (Warehouse, SupplyCache)):
                if u not in self.known_player_structures:
                    self.known_player_structures.append(u)
            if isinstance(u, (Infantry, Tank, Artillery, FPVOperator)):
                if u not in self.known_player_units:
                    self.known_player_units.append(u)
        self.known_player_structures = [s for s in self.known_player_structures if s.is_alive]
        self.known_player_units = [u for u in self.known_player_units if u.is_alive]

    def _calc_advantage(self):
        my = sum(1 for u in self.game.all_units
                 if u.faction == config.ENEMY and u.is_alive
                 and isinstance(u, (Infantry, Tank, Artillery)))
        enemy = sum(1 for u in self.game.all_units
                    if u.faction == config.PLAYER and u.is_alive
                    and isinstance(u, (Infantry, Tank, Artillery)))
        total = my + enemy
        if total == 0:
            return 0.5
        return my / total

    # ── Helpers ────────────────────────────────────────────────────

    def _get_enemy_warehouses(self):
        return [u for u in self.game.all_units
                if isinstance(u, Warehouse) and u.faction == config.ENEMY and u.is_alive]

    def _get_enemy_warehouse(self):
        whs = self._get_enemy_warehouses()
        return whs[0] if whs else None

    def _get_player_base(self):
        for u in self.game.all_units:
            if isinstance(u, Warehouse) and u.faction == config.PLAYER and u.is_alive:
                return u
        return None

    def _get_enemy_drones(self):
        return [u for u in self.game.all_units
                if isinstance(u, ReconDrone) and u.faction == config.ENEMY and u.is_alive]

    def _get_unassigned_units(self):
        assigned = set()
        for g in self.groups:
            for inf in g.infantry:
                assigned.add(id(inf))
            if g.tank:
                assigned.add(id(g.tank))
            if g.artillery:
                assigned.add(id(g.artillery))
            if g.fpv_operator:
                assigned.add(id(g.fpv_operator))
            if g.recon_operator:
                assigned.add(id(g.recon_operator))
            if g.truck:
                assigned.add(id(g.truck))
        result = {'infantry': [], 'tank': [], 'artillery': [],
                  'fpv': [], 'recon': [], 'truck': []}
        for u in self.game.all_units:
            if u.faction != config.ENEMY or not u.is_alive:
                continue
            if id(u) in assigned:
                continue
            if isinstance(u, Infantry):
                result['infantry'].append(u)
            elif isinstance(u, Tank):
                result['tank'].append(u)
            elif isinstance(u, Artillery):
                result['artillery'].append(u)
            elif isinstance(u, FPVOperator):
                result['fpv'].append(u)
            elif isinstance(u, ReconOperator):
                result['recon'].append(u)
            elif isinstance(u, SupplyTruck):
                result['truck'].append(u)
        return result

    def _find_strategic_points(self):
        if self._points_assigned and self._strategic_points:
            return self._strategic_points
        warehouses = self._get_enemy_warehouses()
        if not warehouses:
            return []
        player_base = self._get_player_base()
        per_wh_points = []
        for wh in warehouses:
            candidates = []
            for y in range(self.game.map.height):
                for x in range(self.game.map.width):
                    cell = self.game.map.get_cell(x, y)
                    if not cell:
                        continue
                    if cell.terrain not in (config.FOREST, config.CITY):
                        continue
                    wh_dist = abs(x - wh.x) + abs(y - wh.y)
                    if wh_dist < config.AI_STRATEGIC_POINT_MIN_DIST_WH or wh_dist > config.AI_STRATEGIC_POINT_MAX_DIST_WH:
                        continue
                    if player_base:
                        dist_to_player = abs(x - player_base.x) + abs(y - player_base.y)
                        if dist_to_player < config.AI_STRATEGIC_POINT_MIN_DIST_PLAYER:
                            continue
                    candidates.append((x, y, wh_dist))
            candidates.sort(key=lambda c: c[2])
            wh_pts = []
            for x, y, _ in candidates:
                if len(wh_pts) >= 3:
                    break
                too_close = False
                for px, py in wh_pts:
                    if abs(x - px) + abs(y - py) < config.AI_STRATEGIC_POINT_SPACING:
                        too_close = True
                        break
                if not too_close:
                    wh_pts.append((x, y))
            per_wh_points.append(wh_pts)
        all_points = []
        for pts in per_wh_points:
            for p in pts:
                if p not in all_points:
                    all_points.append(p)
        self._strategic_points = all_points
        self._points_assigned = True
        return all_points

    def _nearest_warehouse(self, x, y):
        whs = self._get_enemy_warehouses()
        if not whs:
            return None
        return min(whs, key=lambda w: abs(w.x - x) + abs(w.y - y))

    def _move_unit_toward(self, unit, tx, ty):
        if unit.moved:
            return False
        if unit.x == tx and unit.y == ty:
            return False
        if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)) and unit.fuel <= 0:
            return False
        path = self.game.map.find_path(unit.x, unit.y, tx, ty,
                                       unit=unit, avoid_occupied=True)
        if not path or len(path) < 2:
            dx = 1 if tx > unit.x else (-1 if tx < unit.x else 0)
            dy = 1 if ty > unit.y else (-1 if ty < unit.y else 0)
            for nx, ny in [(unit.x + dx, unit.y), (unit.x, unit.y + dy), (unit.x + dx, unit.y + dy)]:
                if 0 <= nx < self.game.map.width and 0 <= ny < self.game.map.height:
                    cell = self.game.map.get_cell(nx, ny)
                    if cell and cell.is_walkable and not self._is_occupied(nx, ny, exclude=unit):
                        self.game.map.remove_unit(unit)
                        unit.x, unit.y = nx, ny
                        self.game.map.add_unit(unit, nx, ny)
                        unit.moved = True
                        if isinstance(unit, Infantry):
                            unit.entrenching = False
                        if hasattr(unit, 'fuel'):
                            unit.fuel -= 1
                        return True
            return False
        nx, ny = path[1]
        cell = self.game.map.get_cell(nx, ny)
        if not cell or not cell.is_walkable:
            return False
        self.game.map.remove_unit(unit)
        unit.x, unit.y = nx, ny
        self.game.map.add_unit(unit, nx, ny)
        unit.moved = True
        if isinstance(unit, Infantry):
            unit.entrenching = False
        if hasattr(unit, 'fuel'):
            unit.fuel -= 1
        return True

    def _move_adjacent_to(self, unit, tx, ty):
        if unit.moved:
            return False
        best_adj = None
        best_dist = 999
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < self.game.map.width and 0 <= ny < self.game.map.height:
                cell = self.game.map.get_cell(nx, ny)
                if cell and cell.is_walkable and not self._is_occupied(nx, ny, exclude=unit):
                    d = abs(unit.x - nx) + abs(unit.y - ny)
                    if d < best_dist:
                        best_dist = d
                        best_adj = (nx, ny)
        if not best_adj:
            return False
        if best_dist <= 1:
            self.game.map.remove_unit(unit)
            unit.x, unit.y = best_adj
            self.game.map.add_unit(unit, best_adj[0], best_adj[1])
            unit.moved = True
            if isinstance(unit, Infantry):
                unit.entrenching = False
            return True
        return self._move_unit_toward(unit, best_adj[0], best_adj[1])

    def _is_occupied(self, x, y, exclude=None):
        for u in self.game.all_units:
            if u is exclude:
                continue
            if u.x == x and u.y == y and u.is_alive:
                return True
        return False

    def _clear_warehouse_area(self):
        import random as _rnd
        whs = self._get_enemy_warehouses()
        if not whs:
            return
        assigned_inf_ids = set()
        for g in self.groups:
            for inf in g.infantry:
                assigned_inf_ids.add(id(inf))
        combat_types = (Infantry, Tank, Artillery, FPVOperator, ReconOperator)
        for wh in whs:
            blocked = [u for u in self.game.all_units
                       if u.faction == config.ENEMY and u.is_alive
                       and isinstance(u, combat_types)
                       and (id(u) not in assigned_inf_ids or not isinstance(u, Infantry))
                       and abs(u.x - wh.x) + abs(u.y - wh.y) <= config.AI_CLEAR_WAREHOUSE_RADIUS]
            for unit in blocked:
                if unit.moved:
                    continue
                for _ in range(20):
                    dx = _rnd.randint(-config.AI_CLEAR_WAREHOUSE_RADIUS, config.AI_CLEAR_WAREHOUSE_RADIUS)
                    dy = _rnd.randint(-config.AI_CLEAR_WAREHOUSE_RADIUS, config.AI_CLEAR_WAREHOUSE_RADIUS)
                    nx, ny = wh.x + dx, wh.y + dy
                    nx = max(0, min(self.game.map.width - 1, nx))
                    ny = max(0, min(self.game.map.height - 1, ny))
                    if abs(nx - wh.x) + abs(ny - wh.y) < config.AI_CLEAR_WAREHOUSE_MIN_DIST:
                        continue
                    cell = self.game.map.get_cell(nx, ny)
                    if not cell or not cell.is_walkable:
                        continue
                    if self._is_occupied(nx, ny):
                        continue
                    self.game.map.remove_unit(unit)
                    unit.x, unit.y = nx, ny
                    self.game.map.add_unit(unit, nx, ny)
                    unit.moved = True
                    if isinstance(unit, Infantry):
                        unit.entrenching = False
                    break

    def _group_units(self, group):
        units = list(group.infantry)
        if group.tank:
            units.append(group.tank)
        if group.artillery:
            units.append(group.artillery)
        if group.fpv_operator:
            units.append(group.fpv_operator)
        if group.recon_operator:
            units.append(group.recon_operator)
        return units

    def _move_drone_toward(self, drone, tx, ty, steps=5):
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

    # ── Формирование (кластеризация по складам) ────────────────────

    def _do_form_group(self, action):
        unassigned = self._get_unassigned_units()
        if len(unassigned['infantry']) < config.AI_MIN_INFANTRY_TO_FORM_GROUP:
            return
        warehouses = self._get_enemy_warehouses()
        if not warehouses:
            return
        def _nearest_wh(unit):
            dists = [abs(unit.x - wh.x) + abs(unit.y - wh.y) for wh in warehouses]
            return dists.index(min(dists))
        clusters = {i: {'infantry': [], 'tank': [], 'artillery': [],
                        'fpv': [], 'recon': [], 'truck': []}
                    for i in range(len(warehouses))}
        for key in unassigned:
            for unit in unassigned[key]:
                wi = _nearest_wh(unit)
                clusters[wi][key].append(unit)
        for wi, cl in clusters.items():
            while len(cl['infantry']) >= config.AI_MIN_INFANTRY_TO_FORM_GROUP:
                group = BattleGroup(len(self.groups))
                for _ in range(min(config.AI_MAX_INFANTRY_PER_GROUP, len(cl['infantry']))):
                    group.infantry.append(cl['infantry'].pop(0))
                if cl['tank']:
                    group.tank = cl['tank'].pop(0)
                if cl['artillery']:
                    group.artillery = cl['artillery'].pop(0)
                if cl['fpv']:
                    group.fpv_operator = cl['fpv'].pop(0)
                if cl['recon']:
                    group.recon_operator = cl['recon'].pop(0)
                if cl['truck']:
                    group.truck = cl['truck'].pop(0)
                group.formed = True
                self.groups.append(group)

    # ── Развёртывание ─────────────────────────────────────────────

    def _do_deploy_group(self, action):
        gid = action['group_id']
        if gid >= len(self.groups):
            return
        group = self.groups[gid]
        points = self._find_strategic_points()
        if not group.target_pos:
            if points:
                used = {g.target_pos for g in self.groups if g.target_pos}
                available = [p for p in points if p not in used]
                if not available:
                    available = points
                alive_units = [u for u in self._group_units(group) if u.is_alive]
                if alive_units:
                    avg_x = sum(u.x for u in alive_units) / len(alive_units)
                    avg_y = sum(u.y for u in alive_units) / len(alive_units)
                    best = min(available, key=lambda p: abs(p[0] - avg_x) + abs(p[1] - avg_y))
                    group.target_pos = best
                else:
                    group.target_pos = available[0]
            else:
                return
        if not group.target_pos:
            return
        tx, ty = group.target_pos
        units = self._group_units(group)
        alive_units = [u for u in units if u.is_alive]
        if not alive_units:
            group.deployed = True
            return
        alive_infantry = [u for u in group.infantry if u.is_alive]
        for u in alive_units:
            self._move_unit_toward(u, tx, ty)
        inf_at_pos = all(
            abs(inf.x - tx) + abs(inf.y - ty) <= config.AI_DEPLOY_PROXIMITY
            for inf in alive_infantry
        )
        if inf_at_pos and alive_infantry:
            group.deployed = True
            group.warehouse = self._nearest_warehouse(tx, ty)

    # ── Фортификация: погреб + маршрут снабжения ──────────────────

    def _do_fortify_group(self, action):
        gid = action['group_id']
        if gid >= len(self.groups):
            return
        group = self.groups[gid]

        for inf in group.infantry:
            if not inf.is_alive:
                continue
            cell = self.game.map.get_cell(inf.x, inf.y)
            if cell and not inf.entrenching and cell.entrenchment < inf.max_entrenchment:
                inf.entrenching = True

        if not group.cache:
            builder = None
            for inf in group.infantry:
                if inf.is_alive and not inf.building_cache:
                    builder = inf
                    break
            if builder:
                wh = self._nearest_warehouse(builder.x, builder.y)
                if wh and abs(builder.x - wh.x) + abs(builder.y - wh.y) < config.AI_FORTIFY_MAX_WH_DISTANCE:
                    if group.target_pos:
                        self._move_unit_toward(builder, group.target_pos[0], group.target_pos[1])
                    return
                cache = SupplyCache(builder.x, builder.y, config.ENEMY,
                                    f"Погреб гр.{group.id}")
                builder.building_cache = cache
                self.game.all_units.append(cache)
                self.game.enemy_units.append(cache)
                self.game.map.add_unit(cache, cache.x, cache.y)
                group.cache = cache

        if group.cache and group.cache.is_alive:
            if group.cache.build_turns >= group.cache.build_required:
                if not group.supply_active and group.truck and group.truck.is_alive:
                    wh = group.warehouse or self._nearest_warehouse(group.cache.x, group.cache.y)
                    if wh:
                        group.supply_active = True
                fortified = sum(
                    1 for inf in group.infantry
                    if inf.is_alive and
                    self.game.map.get_cell(inf.x, inf.y) and
                    self.game.map.get_cell(inf.x, inf.y).entrenchment >= inf.max_entrenchment * config.AI_FORTIFY_ENTRENCH_THRESHOLD
                )
                if fortified >= max(1, len(group.infantry) // config.AI_FORTIFY_MIN_FRACTION_DIVISOR):
                    group.fortified = True

    # ── Снабжение: грузовик курсирует склад → погреб ──────────────

    def _do_run_supply(self, action):
        gid = action['group_id']
        if gid >= len(self.groups):
            return
        group = self.groups[gid]
        truck = group.truck
        if not truck or not truck.is_alive:
            return
        wh = group.warehouse or self._nearest_warehouse(truck.x, truck.y)
        if not wh or not wh.is_alive:
            return
        at_wh = abs(truck.x - wh.x) + abs(truck.y - wh.y) <= 1
        has_food = truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0

        if has_food:
            hungry_units = self._find_hungry_units(group)
            for hu in hungry_units:
                self._truck_deliver_food(truck, hu)
            if truck.cargo.get(config.CARGO_SUPPLIES, 0) <= 0:
                return
            cache = group.cache
            if cache and cache.is_alive and cache.build_turns >= cache.build_required:
                if abs(truck.x - cache.x) + abs(truck.y - cache.y) <= 1:
                    self._truck_unload(truck, cache)
                    return
                if not truck.moved:
                    self._move_truck_toward(truck, cache.x, cache.y)
                return
            return

        if at_wh:
            self._truck_load_supplies_only(truck, wh)
        elif not truck.moved:
            self._move_adjacent_to(truck, wh.x, wh.y)

    def _move_truck_toward(self, truck, tx, ty):
        if truck.moved:
            return False
        if truck.x == tx and truck.y == ty:
            return False
        path = self.game.map.find_path(truck.x, truck.y, tx, ty,
                                       unit=truck, avoid_occupied=False)
        if not path or len(path) < 2:
            return False
        nx, ny = path[1]
        cell = self.game.map.get_cell(nx, ny)
        if not cell or not cell.is_walkable:
            return False
        self.game.map.remove_unit(truck)
        truck.x, truck.y = nx, ny
        self.game.map.add_unit(truck, nx, ny)
        truck.moved = True
        return True

    def _truck_load_supplies_only(self, truck, origin):
        available = getattr(origin, 'supplies', 0)
        if available <= 0:
            return
        want = min(config.AI_TRUCK_LOAD_LIMIT, available)
        taken = truck.load_by_weight(config.CARGO_SUPPLIES, want)
        if taken > 0:
            origin.supplies -= taken

    def _find_hungry_units(self, group):
        threshold = config.SOLDIER_MAX_FOOD * config.AI_HUNGRY_THRESHOLD_FRACTION
        units = self._group_units(group)
        hungry = []
        for u in units:
            if not u.is_alive:
                continue
            if isinstance(u, Infantry):
                for s in u.alive_soldiers:
                    if s.food < threshold:
                        hungry.append(u)
                        break
            elif hasattr(u, 'food') and hasattr(u, 'max_food') and u.max_food > 0:
                if u.food < threshold:
                    hungry.append(u)
        return hungry

    def _find_hungry_unit(self, group):
        units = self._find_hungry_units(group)
        return units[0] if units else None

    def _truck_deliver_food(self, truck, target):
        if isinstance(target, Infantry):
            for s in target.alive_soldiers:
                if s.food < s.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                    given = truck.unload(config.CARGO_SUPPLIES, s.max_food - s.food)
                    s.food += given
        elif hasattr(target, 'carry_food') and hasattr(target, 'max_carry_food'):
            if target.carry_food < target.max_carry_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                given = truck.unload(config.CARGO_SUPPLIES, target.max_carry_food - target.carry_food)
                target.carry_food += given
        elif hasattr(target, 'food') and hasattr(target, 'max_food'):
            if target.food < target.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                given = truck.unload(config.CARGO_SUPPLIES, target.max_food - target.food)
                target.food += given

    def _truck_load(self, truck, origin):
        cargo_map = {
            config.CARGO_SUPPLIES: 'supplies',
            config.CARGO_AMMO: 'ammo',
            config.CARGO_FUEL: 'fuel',
            config.CARGO_BATTERIES: 'batteries',
        }
        for ct in [config.CARGO_SUPPLIES, config.CARGO_AMMO, config.CARGO_FUEL, config.CARGO_BATTERIES]:
            attr = cargo_map.get(ct, ct)
            available = getattr(origin, attr, 0)
            if available <= 0:
                continue
            want = min(config.AI_TRUCK_LOAD_PER_RESOURCE, available)
            taken = truck.load_by_weight(ct, want)
            if taken > 0:
                setattr(origin, attr, getattr(origin, attr, 0) - taken)
                if truck.weight_remaining <= 0:
                    break

    def _truck_unload(self, truck, dest):
        cargo_map = {
            config.CARGO_SUPPLIES: 'supplies',
            config.CARGO_AMMO: 'ammo',
            config.CARGO_FUEL: 'fuel',
            config.CARGO_BATTERIES: 'batteries',
        }
        for ct in [config.CARGO_SUPPLIES, config.CARGO_AMMO, config.CARGO_FUEL, config.CARGO_BATTERIES]:
            available = truck.cargo.get(ct, 0)
            if available <= 0:
                continue
            attr = cargo_map.get(ct, ct)
            mx = getattr(dest, f"max_{attr}", 999999)
            cur = getattr(dest, attr, 0)
            space = mx - cur
            if space <= 0:
                continue
            if isinstance(dest, SupplyCache) and hasattr(dest, 'slots_remaining'):
                if dest.slots_remaining <= 0:
                    break
                give = min(available, space, dest.slots_remaining)
            else:
                give = min(available, space)
            given = truck.unload(ct, give)
            if given > 0:
                setattr(dest, attr, getattr(dest, attr, 0) + given)

    # ── FPV операторы подтягиваются к целям ────────────────────────

    def _reposition_fpv_operators(self):
        for group in self.groups:
            op = group.fpv_operator
            if not op or not op.is_alive:
                continue
            if op.fpv_stock <= 0:
                continue
            targets = [u for u in self.game.all_units
                       if u.faction == config.PLAYER and u.is_alive
                       and not isinstance(u, (ReconDrone, FPVDrone,
                                              Warehouse, SupplyCache))]
            if not targets:
                continue
            closest = min(targets,
                          key=lambda t: abs(t.x - op.x) + abs(t.y - op.y))
            dist = abs(closest.x - op.x) + abs(closest.y - op.y)
            if dist > config.FPV_OPERATOR_RANGE:
                self._move_unit_toward(op, closest.x, closest.y)

    # ── Наступление (при преимуществе) ─────────────────────────

    def _do_offensive(self, action):
        if not self.groups:
            return
        if self.known_player_units:
            target = self.known_player_units[0]
        elif self.known_player_structures:
            target = self.known_player_structures[0]
        else:
            player_base = self._get_player_base()
            if player_base:
                target = player_base
            else:
                return
        half = max(1, len(self.groups) // config.AI_OFFENSIVE_GROUP_FRACTION)
        for gi, group in enumerate(self.groups):
            if gi >= half:
                break
            combat_units = []
            for inf in group.infantry:
                if inf.is_alive:
                    combat_units.append(inf)
            if group.tank and group.tank.is_alive:
                combat_units.append(group.tank)
            for unit in combat_units:
                if unit.moved:
                    continue
                dist = abs(unit.x - target.x) + abs(unit.y - target.y)
                attack_range = 2 if isinstance(unit, Tank) else 1
                if dist <= attack_range and unit.ammo > 0:
                    result = self.game.resolve_attack(unit, target)
                    if result:
                        self.game.combat_log.append(result)
                    continue
                self._move_unit_toward(unit, target.x, target.y)

    # ── Оборона ────────────────────────────────────────────────────

    def _do_defensive_ops(self, action):
        for group in self.groups:
            for inf in group.infantry:
                if inf.is_alive and not inf.entrenching:
                    cell = self.game.map.get_cell(inf.x, inf.y)
                    if cell and cell.terrain in (config.FOREST, config.CITY):
                        if cell.entrenchment < inf.max_entrenchment:
                            inf.entrenching = True

    # ── Разведка ───────────────────────────────────────────────────

    def _do_deploy_recon(self, action):
        wh = self._get_enemy_warehouse()
        if not wh or wh.batteries < config.DRONE_SPAWN_BATTERY_COST:
            return
        existing = [u for u in self.game.all_units
                    if isinstance(u, ReconDrone) and u.faction == config.ENEMY
                    and u.is_alive]
        if len(existing) >= config.AI_MAX_DRONES:
            return
        player_base = self._get_player_base()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = wh.x + dx, wh.y + dy
            cell = self.game.map.get_cell(nx, ny)
            if cell and cell.is_walkable and not self._is_occupied(nx, ny):
                drone = ReconDrone(nx, ny, config.ENEMY, "Вражеский дрон")
                self.game.all_units.append(drone)
                self.game.enemy_units.append(drone)
                self.game.map.add_unit(drone, nx, ny)
                wh.batteries -= config.DRONE_SPAWN_BATTERY_COST
                if player_base and self.turn_count >= config.AI_DRONE_SCOUT_START_TURN:
                    px = player_base.x + random.randint(-config.AI_DRONE_PATROL_OFFSET, config.AI_DRONE_PATROL_OFFSET)
                    py = player_base.y + random.randint(-config.AI_DRONE_PATROL_OFFSET, config.AI_DRONE_PATROL_OFFSET)
                    px = max(0, min(self.game.map.width - 1, px))
                    py = max(0, min(self.game.map.height - 1, py))
                    self.drone_targets[id(drone)] = (px, py)
                break

    # ── Артиллерия ─────────────────────────────────────────────────

    def _do_artillery_target(self, action):
        for group in self.groups:
            art = group.artillery
            if not art or not art.is_alive:
                continue
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
                    val = config.ARTILLERY_TARGET_PRIORITY_WAREHOUSE
                elif isinstance(u, SupplyCache):
                    val = config.ARTILLERY_TARGET_PRIORITY_CACHE
                elif isinstance(u, Tank):
                    val = config.ARTILLERY_TARGET_PRIORITY_TANK
                elif isinstance(u, Artillery):
                    val = config.ARTILLERY_TARGET_PRIORITY_ARTILLERY
                elif isinstance(u, Infantry):
                    val = config.ARTILLERY_TARGET_PRIORITY_INFANTRY
                elif isinstance(u, FPVOperator):
                    val = config.ARTILLERY_TARGET_PRIORITY_OPERATOR
                if val > best_val:
                    best_val = val
                    best = u
            if best:
                art.pending_target = (best.x, best.y)

    # ── Управление дронами ─────────────────────────────────────────

    def _manage_drones(self):
        if self.turn_count < config.AI_DRONE_MANAGEMENT_START_TURN:
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
                if isinstance(unit, ReconDrone):
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
                    px = player_base.x + random.randint(-config.AI_DRONE_PATROL_OFFSET_INITIAL, config.AI_DRONE_PATROL_OFFSET_INITIAL)
                    py = player_base.y + random.randint(-config.AI_DRONE_PATROL_OFFSET_INITIAL, config.AI_DRONE_PATROL_OFFSET_INITIAL)
                else:
                    px = random.randint(0, self.game.map.width - 1)
                    py = random.randint(0, self.game.map.height - 1)
                px = max(0, min(self.game.map.width - 1, px))
                py = max(0, min(self.game.map.height - 1, py))
                self.drone_targets[drone_id] = (px, py)
            target = self.drone_targets[drone_id]
            dist_to_target = abs(drone.x - target[0]) + abs(drone.y - target[1])
            if dist_to_target <= 1:
                if player_base:
                    px = player_base.x + random.randint(-config.AI_DRONE_PATROL_OFFSET_RETARGET, config.AI_DRONE_PATROL_OFFSET_RETARGET)
                    py = player_base.y + random.randint(-config.AI_DRONE_PATROL_OFFSET_RETARGET, config.AI_DRONE_PATROL_OFFSET_RETARGET)
                else:
                    px = random.randint(0, self.game.map.width - 1)
                    py = random.randint(0, self.game.map.height - 1)
                px = max(0, min(self.game.map.width - 1, px))
                py = max(0, min(self.game.map.height - 1, py))
                self.drone_targets[drone_id] = (px, py)
            else:
                self._move_drone_toward(drone, target[0], target[1])

    def cleanup_drone_state(self):
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
