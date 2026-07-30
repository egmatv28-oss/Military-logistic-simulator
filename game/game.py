from . import config
from .map_ import GameMap
from .units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, FPVOperator, ReconOperator, Artillery, SoldierUnit, RadarEW, SupplyCache
from .combat import resolve_attack
from .controllers import AIController, HumanController
from .resource_transfer import transfer as _rt_transfer, can_accept_resource as _rt_can_accept
from .turn_manager import TurnManager
from .action_manager import ActionManager
from .supply_logistics import SupplyLogistics
from .unit_animation import UnitAnimation


class Game:
    def __init__(self, game_mode="ai"):
        self.map = GameMap(config.MAP_WIDTH, config.MAP_HEIGHT)
        self.turn = 0
        self.max_turns = config.MAX_TURNS
        self.phase = config.PHASE_PLANNING
        self.phase_timer = 0
        self.phase_auto_advance = False
        self.game_over = False
        self.victory = False
        self.message = "Добро пожаловать! Отдайте приказы и нажмите Enter"
        self.combat_log = []
        self.fpv_drones_in_flight = []
        self.fpv_launched_this_turn = 0
        self.combat_effects = []
        self.selected_unit = None
        self.hovered_cell = None
        self.pinned_cell = None
        self.moving_warehouse = False
        self.radar_mode = False
        self.join_move_mode = False
        self.supply_line_select_mode = None
        self.origin_select_mode = None
        self.dest_select_mode = None
        self.deliver_target_mode = None
        self.artillery_barrage_mode = None
        self.soldier_management_mode = False
        self.selected_soldier_idx = None
        self.soldier_source_unit = None
        self.soldier_transfer_mode = False
        self.soldier_transfer_target = None
        self.soldier_detail_idx = None
        self.waypoints = {}
        self.all_units = []
        self.player_units = []
        self.enemy_units = []
        self.dead_units = []

        self._anim_queue = []
        self._anim_active = False
        self._anim_unit = None
        self._anim_path = []
        self._anim_step = 0
        self._anim_timer = 0
        self._anim_delay = 15
        self._anim_callback = None

        self.transfer_mode = False
        self.transfer_source = None
        self.transfer_resource = None
        self.cargo_transfer_mode = False
        self.cargo_transfer_truck = None
        self.cargo_transfer_type = None
        self.cargo_transfer_source = None
        self.cargo_transfer_target = None
        self.cargo_transfer_timer = 0

        self.game_mode = game_mode
        self.current_player_faction = config.PLAYER
        self.waiting_for_hotseat_switch = False
        self.hotseat_switch_message = ""
        self.ui = None
        self.reveal_all_enemies = False
        self.fog_disabled = False

        if game_mode == "ai":
            self.player_controller = HumanController(self, config.PLAYER)
            self.enemy_controller = AIController(self, config.ENEMY)
        else:
            self.player_controller = HumanController(self, config.PLAYER)
            self.enemy_controller = HumanController(self, config.ENEMY)

        self.reinforcement_timers = {
            'infantry': config.REINFORCEMENT_INFANTRY_INTERVAL,
            'tank': config.REINFORCEMENT_TANK_INTERVAL,
            'drone': config.REINFORCEMENT_DRONE_INTERVAL,
            'fpv': config.REINFORCEMENT_FPV_INTERVAL,
        }

        self._turn_mgr = TurnManager(self)
        self._action_mgr = ActionManager(self)
        self._supply_mgr = SupplyLogistics(self)
        self._anim_mgr = UnitAnimation(self)

        self._setup()

    def _setup(self):
        import random as _rnd

        def _find_free_cell(base_x, base_y, attempts=50):
            for _ in range(attempts):
                ox = base_x + _rnd.randint(-2, 2)
                oy = base_y + _rnd.randint(-2, 2)
                ox = max(1, min(self.map.width - 2, ox))
                oy = max(1, min(self.map.height - 2, oy))
                cell = self.map.get_cell(ox, oy)
                if cell and cell.is_walkable and cell.terrain != config.RIVER and len(cell.units) == 0:
                    return ox, oy
            return base_x, base_y

        def _spawn_units_for_faction(faction, unit_list, base_x, base_y, prefix, is_enemy=False):
            wh = Warehouse(base_x, base_y, faction, f"{prefix}Штаб" if not is_enemy else "Склад врага")
            self.all_units.append(wh)
            unit_list.append(wh)
            self.map.add_unit(wh, base_x, base_y)

            infantry_names = [
                "Альфа", "Браво", "Чарли", "Дельта", "Эхо",
                "Фокстрот", "Гольф", "Отель", "Индия", "Джульетта"
            ]
            for i in range(10):
                ix, iy = _find_free_cell(base_x + (1 if not is_enemy else -1), base_y - 2 + i)
                name = f"{prefix}Пехота-{infantry_names[i]}"
                inf = Infantry(ix, iy, faction, name)
                self.all_units.append(inf)
                unit_list.append(inf)
                self.map.add_unit(inf, ix, iy)

            for i in range(5):
                tx, ty = _find_free_cell(base_x + (2 if not is_enemy else -2), base_y - 1 + i)
                name = f"{prefix}Танк-{i+1}"
                tank = Tank(tx, ty, faction, name)
                self.all_units.append(tank)
                unit_list.append(tank)
                self.map.add_unit(tank, tx, ty)

            for i in range(3):
                ax, ay = _find_free_cell(base_x + (-1 if not is_enemy else 1), base_y - 1 + i)
                name = f"{prefix}Артиллерия-{i+1}"
                art = Artillery(ax, ay, faction, name)
                self.all_units.append(art)
                unit_list.append(art)
                self.map.add_unit(art, ax, ay)

            for i in range(3):
                fx, fy = _find_free_cell(base_x, base_y + 1 + i)
                name = f"{prefix}FPV-{i+1}"
                fpv = FPVOperator(fx, fy, faction, name)
                self.all_units.append(fpv)
                unit_list.append(fpv)
                self.map.add_unit(fpv, fx, fy)

            for i in range(3):
                rx, ry = _find_free_cell(base_x + (-2 if not is_enemy else 2), base_y - 1 + i)
                name = f"{prefix}Оператор БПЛА-{i+1}"
                recon_op = ReconOperator(rx, ry, faction, name)
                self.all_units.append(recon_op)
                unit_list.append(recon_op)
                self.map.add_unit(recon_op, rx, ry)

            for i in range(5):
                sx, sy = _find_free_cell(base_x + (1 if not is_enemy else -1), base_y + 2 + i)
                name = f"{prefix}Грузовик-{i+1}"
                truck = SupplyTruck(sx, sy, faction, name)
                self.all_units.append(truck)
                unit_list.append(truck)
                self.map.add_unit(truck, sx, sy)

        wx, wy = self.map.player_warehouse
        _spawn_units_for_faction(config.PLAYER, self.player_units, wx, wy, "", is_enemy=False)

        for ex, ey in self.map.enemy_warehouses:
            _spawn_units_for_faction(config.ENEMY, self.enemy_units, ex, ey, "Вражеский-", is_enemy=True)

        self._update_visibility_for_current_faction()

    # ── properties (stay on Game) ────────────────────────────────────

    @property
    def player_combat_units(self):
        return [u for u in self.player_units if isinstance(u, (Infantry, Tank))]

    def is_player_turn(self):
        return self.current_player_faction == config.PLAYER

    def get_current_controller(self):
        if self.current_player_faction == config.PLAYER:
            return self.player_controller
        return self.enemy_controller

    def get_active_units(self):
        if self.current_player_faction == config.PLAYER:
            return self.player_units
        return self.enemy_units

    def get_enemy_units_for_faction(self):
        if self.current_player_faction == config.PLAYER:
            return self.enemy_units
        return self.player_units

    def get_unit_max_move(self, unit):
        if isinstance(unit, ReconDrone):
            return config.DRONE_MOVE_POINTS
        elif isinstance(unit, SoldierUnit):
            return config.SOLDIER_UNIT_MOVE_POINTS
        elif isinstance(unit, Tank):
            return config.TANK_MOVE_POINTS
        elif isinstance(unit, SupplyTruck):
            return config.TRUCK_MOVE_POINTS
        elif isinstance(unit, Artillery):
            return config.ARTILLERY_MOVE_POINTS
        elif isinstance(unit, Infantry):
            return config.INFANTRY_MOVE_POINTS
        elif isinstance(unit, RadarEW):
            return config.RADAR_EW_MOVE_POINTS
        return config.INFANTRY_MOVE_POINTS

    def get_unit_max_steps(self, unit):
        if isinstance(unit, ReconDrone):
            return config.DRONE_STEPS_PER_TURN
        elif isinstance(unit, SoldierUnit):
            return config.SOLDIER_STEPS_PER_TURN
        elif isinstance(unit, Tank):
            return config.TANK_STEPS_PER_TURN
        elif isinstance(unit, SupplyTruck):
            return config.TRUCK_STEPS_PER_TURN
        elif isinstance(unit, Artillery):
            return config.ARTILLERY_STEPS_PER_TURN
        elif isinstance(unit, Infantry):
            return config.INFANTRY_STEPS_PER_TURN
        elif isinstance(unit, RadarEW):
            return config.RADAR_EW_STEPS_PER_TURN
        return config.INFANTRY_STEPS_PER_TURN

    def resolve_attack(self, attacker, defender):
        return resolve_attack(attacker, defender, self.map)

    def _add_resource_transfer_effect(self, source, target):
        self.combat_effects.append({
            'x': (source.x + target.x) / 2,
            'y': (source.y + target.y) / 2,
            'type': 'resource_transfer',
            'timer': 20,
            'source': source,
            'target': target,
        })

    def check_jamming(self):
        for unit in self.all_units:
            if isinstance(unit, ReconOperator) and unit.drone and unit.drone.is_alive:
                drone = unit.drone
                jammed = self._is_line_jammed(unit.x, unit.y, drone.x, drone.y)
                drone.jammed = jammed
                if jammed:
                    drone.jam_turns += 1
                else:
                    drone.jam_turns = 0

    def _is_line_jammed(self, x1, y1, x2, y2):
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steps = max(dx, dy)
        if steps == 0:
            return False
        
        # Проверяем RadarEW юниты в радиусе действия
        for unit in self.all_units:
            if unit.is_alive and isinstance(unit, RadarEW) and unit.active:
                # Проверяем расстояние от RadarEW до линии
                if self._distance_to_line(unit.x, unit.y, x1, y1, x2, y2) <= unit.jam_range:
                    return True
        
        # Проверяем другие jammer юниты на линии
        for i in range(steps + 1):
            t = i / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            
            cell = self.map.get_cell(x, y)
            if cell:
                for unit in cell.units:
                    if unit.is_alive and hasattr(unit, 'is_jammer') and unit.is_jammer and not isinstance(unit, RadarEW):
                        return True
        return False

    def _distance_to_line(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return abs(px - x1) + abs(py - y1)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return abs(px - proj_x) + abs(py - proj_y)

    # ── delegation: TurnManager ──────────────────────────────────────

    def end_planning_phase(self):
        self._turn_mgr.end_planning_phase()

    def _advance_phase(self):
        self._turn_mgr.advance_phase()

    def _do_movement_phase(self):
        self._turn_mgr._do_movement_phase()

    def _auto_attack_adjacent(self):
        self._turn_mgr._auto_attack_adjacent()

    def _do_detection_phase(self):
        self._turn_mgr._do_detection_phase()

    def _do_ranged_combat_phase(self):
        self._turn_mgr._do_ranged_combat_phase()

    def _resolve_artillery_attacks(self):
        self._turn_mgr._resolve_artillery_attacks()

    def _find_artillery_target(self, artillery, faction):
        return self._turn_mgr._find_artillery_target(artillery, faction)

    def _resolve_fpv_attacks(self):
        self._turn_mgr._resolve_fpv_attacks()

    def _cleanup_dead_drone(self, drone):
        self._turn_mgr._cleanup_dead_drone(drone)

    def _create_fpv_drones(self):
        self._turn_mgr._create_fpv_drones()

    def _is_drone_detected(self, enemy_drone, friendly_drones):
        return self._turn_mgr._is_drone_detected(enemy_drone, friendly_drones)

    def _do_close_combat_phase(self):
        self._turn_mgr._do_close_combat_phase()

    def _do_logistics_phase(self):
        self._turn_mgr._do_logistics_phase()

    def _do_entrench_phase(self):
        self._turn_mgr._do_entrench_phase()

    def _do_enemy_turn(self):
        self._turn_mgr._do_enemy_turn()

    def _end_turn(self):
        self._turn_mgr.end_turn()

    def _update_visibility_for_current_faction(self):
        self._turn_mgr._update_visibility_for_current_faction()

    def _switch_current_player(self):
        self._turn_mgr._switch_current_player()

    def confirm_hotseat_switch(self):
        self._turn_mgr.confirm_hotseat_switch()

    def _add_combat_effect(self, x, y, effect_type, hits=None):
        self._turn_mgr._add_combat_effect(x, y, effect_type, hits)

    def _add_projectile_effect(self, src_x, src_y, dst_x, dst_y, effect_type="artillery_shell"):
        self._turn_mgr._add_projectile_effect(src_x, src_y, dst_x, dst_y, effect_type)

    def _update_combat_effects(self):
        self._turn_mgr._update_combat_effects()

    def _auto_resupply_units(self):
        self._turn_mgr._auto_resupply_units()

    def _auto_resupply_from_caches(self):
        self._turn_mgr._auto_resupply_from_caches()

    def _process_reinforcements(self):
        self._turn_mgr._process_reinforcements()

    def _spawn_infantry(self):
        self._turn_mgr._spawn_infantry()

    def _spawn_tank(self):
        self._turn_mgr._spawn_tank()

    def _spawn_drone(self):
        self._turn_mgr._spawn_drone()

    def _spawn_fpv_operator(self):
        self._turn_mgr._spawn_fpv_operator()

    def get_reinforcement_info(self):
        return self._turn_mgr.get_reinforcement_info()

    def order_artillery_attack(self, target_x, target_y):
        self._turn_mgr.order_artillery_attack(target_x, target_y)

    def order_artillery_barrage(self):
        self._turn_mgr.order_artillery_barrage()

    def confirm_artillery_barrage(self, target_x, target_y):
        self._turn_mgr.confirm_artillery_barrage(target_x, target_y)

    def update(self):
        self._cleanup_dead_units()
        self.check_jamming()
        self._turn_mgr.update()

    def _cleanup_dead_units(self):
        dead = []
        for u in self.all_units:
            if not u.is_alive:
                dead.append(u)
            elif hasattr(u, 'crew') and hasattr(u, 'soldiers_list') and u.crew <= 0 and not isinstance(u, (Warehouse, SupplyCache)):
                u.die()
                dead.append(u)
        for u in dead:
            if u in self.all_units:
                self.all_units.remove(u)
            if u in self.player_units:
                self.player_units.remove(u)
            if u in self.enemy_units:
                self.enemy_units.remove(u)
            if u not in self.dead_units:
                self.dead_units.append(u)
            if u in self.waypoints:
                del self.waypoints[u]
            if self.selected_unit is u:
                self.selected_unit = None

    # ── delegation: ActionManager ────────────────────────────────────

    def select_unit(self, unit):
        self._action_mgr.select_unit(unit)

    def select_unit_at(self, x, y):
        self._action_mgr.select_unit_at(x, y)

    def move_selected_unit(self, tx, ty):
        return self._action_mgr.move_selected_unit(tx, ty)

    def order_transfer_cargo(self, target_unit=None):
        return self._action_mgr.order_transfer_cargo(target_unit)

    def _find_nearest_cargo_target(self, source):
        return self._action_mgr._find_nearest_cargo_target(source)

    def transfer_resource_by_type(self, source, target, res_type):
        return self._action_mgr.transfer_resource_by_type(source, target, res_type)

    def _can_accept_cargo(self, unit):
        return self._action_mgr._can_accept_cargo(unit)

    def _do_cargo_transfer(self, source, target):
        return self._action_mgr._do_cargo_transfer(source, target)

    def start_transfer_mode(self, resource_type):
        self._action_mgr.start_transfer_mode(resource_type)

    def confirm_transfer_to_target(self, target):
        return self._action_mgr.confirm_transfer_to_target(target)

    def cancel_transfer_mode(self):
        self._action_mgr.cancel_transfer_mode()

    def order_entrench(self):
        self._action_mgr.order_entrench()

    def order_build_cache(self):
        self._action_mgr.order_build_cache()

    def order_unload_ammo(self):
        unit = self.selected_unit
        if not unit or not unit.is_alive:
            self.message = "Выберите юнит"
            return
        if not hasattr(unit, 'ammo') or unit.ammo <= 0:
            self.message = "Нет боезапаса для выгрузки"
            return
        cell = self.map.get_cell(unit.x, unit.y)
        if not cell:
            return
        for u in cell.units:
            if u is not unit and u.is_alive and u.faction == unit.faction and hasattr(u, 'ammo') and hasattr(u, 'max_ammo'):
                if u.ammo < u.max_ammo:
                    give = min(unit.ammo, u.max_ammo - u.ammo)
                    unit.ammo -= give
                    u.ammo += give
                    self.message = f"Передано {give} боезапаса → {u.name}"
                    return
        self.message = "Нет подходящего юнита рядом"

    def order_form_squad(self):
        return self._action_mgr.order_form_squad()

    def order_join_squad(self):
        return self._action_mgr.order_join_squad()

    def order_join_squad_move(self):
        return self._action_mgr.order_join_squad_move()

    def order_load_single_to_truck(self):
        return self._action_mgr.order_load_single_to_truck()

    def enter_soldier_management(self, unit):
        self._action_mgr.enter_soldier_management(unit)

    def exit_soldier_management(self):
        self._action_mgr.exit_soldier_management()

    def select_soldier_for_transfer(self, idx):
        self._action_mgr.select_soldier_for_transfer(idx)

    def confirm_transfer_soldier(self, target_unit):
        return self._action_mgr.confirm_transfer_soldier(target_unit)

    def load_soldier_to_truck(self, soldier, truck):
        return self._action_mgr.load_soldier_to_truck(soldier, truck)

    def send_soldier_to_reserve(self, soldier):
        return self._action_mgr.send_soldier_to_reserve(soldier)

    def order_exit_garrison(self):
        self._action_mgr.order_exit_garrison()

    def order_attack(self, target):
        return self._action_mgr.order_attack(target)

    def order_attack_cell(self, gx, gy):
        return self._action_mgr.order_attack_cell(gx, gy)

    def order_fpv_strike(self, target):
        return self._action_mgr.order_fpv_strike(target)

    def start_move_warehouse(self):
        self._action_mgr.start_move_warehouse()

    def confirm_move_warehouse(self, tx, ty):
        self._action_mgr.confirm_move_warehouse(tx, ty)

    # ── delegation: SupplyLogistics ──────────────────────────────────

    def order_start_supply_line(self):
        self._supply_mgr.order_start_supply_line()

    def order_assign_supply_dest(self, gx, gy):
        self._supply_mgr.order_assign_supply_dest(gx, gy)

    def order_set_origin(self):
        self._supply_mgr.order_set_origin()

    def order_set_dest(self):
        self._supply_mgr.order_set_dest()

    def confirm_set_origin(self, gx, gy):
        self._supply_mgr.confirm_set_origin(gx, gy)

    def confirm_set_dest(self, gx, gy):
        self._supply_mgr.confirm_set_dest(gx, gy)

    def _try_start_route(self, truck):
        self._supply_mgr._try_start_route(truck)

    def order_cancel_supply_line(self):
        self._supply_mgr.order_cancel_supply_line()

    def order_deliver_to_unit(self):
        self._supply_mgr.order_deliver_to_unit()

    def confirm_deliver_to_unit(self, gx, gy):
        self._supply_mgr.confirm_deliver_to_unit(gx, gy)

    def load_truck(self, load_type=None):
        self._supply_mgr.load_truck(load_type)

    def unload_truck(self):
        self._supply_mgr.unload_truck()

    def _auto_unload_to_target(self, truck, target):
        self._supply_mgr._auto_unload_to_target(truck, target)

    def load_operator_batteries(self):
        self._supply_mgr.load_operator_batteries()

    def transfer_from_cache_to_unit(self, cache, target):
        return self._supply_mgr.transfer_from_cache_to_unit(cache, target)

    def warehouse_transfer_to_unit_direct(self, target):
        return self._supply_mgr.warehouse_transfer_to_unit_direct(target)

    def warehouse_transfer_to_unit(self):
        self._supply_mgr.warehouse_transfer_to_unit()

    def _process_supply_routes(self):
        self._supply_mgr.process_supply_routes()

    def _truck_load(self, truck, origin):
        self._supply_mgr._truck_load(truck, origin)

    def _truck_unload(self, truck, dest):
        self._supply_mgr._truck_unload(truck, dest)

    def _set_supply_waypoint(self, truck, tx, ty):
        self._supply_mgr._set_supply_waypoint(truck, tx, ty)

    def _find_adjacent(self, target, mover):
        return self._supply_mgr._find_adjacent(target, mover)

    def _transfer_to_truck(self, truck, source):
        return self._supply_mgr.transfer_to_truck(truck, source)

    def _transfer_from_truck(self, truck, dest):
        return self._supply_mgr.transfer_from_truck(truck, dest)

    def _can_occupy(self, unit, x, y):
        return self._supply_mgr._can_occupy(unit, x, y)

    def set_waypoint_destination(self, unit, tx, ty):
        return self._supply_mgr.set_waypoint_destination(unit, tx, ty)

    def set_waypoint(self, unit, path_nodes):
        self._supply_mgr.set_waypoint(unit, path_nodes)

    def clear_waypoints(self, unit):
        self._supply_mgr.clear_waypoints(unit)

    def _process_waypoints(self):
        self._supply_mgr.process_waypoints()

    # ── delegation: UnitAnimation ────────────────────────────────────

    def _start_unit_animation(self, unit, path, callback=None):
        self._anim_mgr.start_unit_animation(unit, path, callback)

    def _queue_movement_animation(self, unit, path, callback=None):
        self._anim_mgr.queue_movement_animation(unit, path, callback)

    def _update_movement_animation(self):
        self._anim_mgr.update_movement_animation()

    def is_animating(self):
        return self._anim_mgr.is_animating()
