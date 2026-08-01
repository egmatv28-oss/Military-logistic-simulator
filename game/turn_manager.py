import random
from . import config
from .units import (Infantry, Tank, ReconDrone, FPVDrone, SupplyTruck,
                    Warehouse, FPVOperator, ReconOperator, SupplyCache,
                    Artillery, SoldierUnit, RadarEW)
from .combat import resolve_attack


class TurnManager:
    """Turn lifecycle: phases, end-of-turn, reinforcements, hot-seat switching."""

    def __init__(self, game):
        self.game = game

    # ── phase control ────────────────────────────────────────────────

    def end_planning_phase(self):
        g = self.game
        g.phase = config.PHASE_MOVEMENT
        g.phase_timer = config.PHASE_TIMER_PLANNING
        self.advance_phase()

    def advance_phase(self):
        g = self.game
        if g.phase == config.PHASE_MOVEMENT:
            self._do_movement_phase()
            g.phase = config.PHASE_DETECTION
        elif g.phase == config.PHASE_DETECTION:
            self._do_detection_phase()
            g.phase = config.PHASE_RANGED_COMBAT
        elif g.phase == config.PHASE_RANGED_COMBAT:
            self._do_ranged_combat_phase()
            g.phase = config.PHASE_CLOSE_COMBAT
        elif g.phase == config.PHASE_CLOSE_COMBAT:
            self._do_close_combat_phase()
            g.phase = config.PHASE_LOGISTICS
        elif g.phase == config.PHASE_LOGISTICS:
            self._do_logistics_phase()
            g.phase = config.PHASE_ENTRENCH
        elif g.phase == config.PHASE_ENTRENCH:
            self._do_entrench_phase()
            g.phase = config.PHASE_ENEMY_TURN
        elif g.phase == config.PHASE_ENEMY_TURN:
            self._do_enemy_turn()
            self.end_turn()
            g.phase = config.PHASE_PLANNING

    # ── movement phase ───────────────────────────────────────────────

    def _do_movement_phase(self):
        g = self.game
        self._auto_resupply_units()
        self._create_fpv_drones()

        for drone in list(g.fpv_drones_in_flight):
            if not drone.is_alive:
                self._cleanup_dead_drone(drone)
                continue
            if not drone.target or not drone.target.is_alive:
                drone.die()
                self._cleanup_dead_drone(drone)
                continue
            drone.age += 1
            if drone.age > FPVDrone.MAX_AGE:
                drone.die()
                self._cleanup_dead_drone(drone)
                continue
            if not drone.moved:
                drone.move_toward_target(g.map)
                if drone.reached:
                    g.message = f"{drone.name} достиг цели!"
        g._process_waypoints()
        g._process_supply_routes()
        self._auto_attack_adjacent()

    def _auto_attack_adjacent(self):
        g = self.game
        combat_units = [u for u in g.all_units if isinstance(u, (Infantry, Tank)) and u.is_alive]
        for unit in combat_units:
            if unit.attacked or getattr(unit, 'is_understaffed', False):
                continue
            for other in combat_units:
                if other.faction == unit.faction or not other.is_alive:
                    continue
                dist = abs(unit.x - other.x) + abs(unit.y - other.y)
                if dist == 1:
                    result = resolve_attack(unit, other)
                    if result:
                        g.combat_log.append(result)
                        anim_type = result.get('animation', 'attack')
                        self._add_combat_effect(unit.x, unit.y, anim_type, result.get('hits'))
                        if result.get("defender") and not result["defender"].is_alive:
                            g.message = f"{unit.name} уничтожил {other.name}!"
                        else:
                            g.message = result.get('message', f"{unit.name} атакует {other.name}")
                    break
            if unit.attacked:
                continue
            for target in g.all_units:
                if not target.is_alive or target.faction == unit.faction:
                    continue
                if not isinstance(target, (ReconOperator, FPVOperator, Warehouse, SupplyCache)):
                    continue
                dist = abs(unit.x - target.x) + abs(unit.y - target.y)
                if dist == 1:
                    if isinstance(target, (Warehouse, SupplyCache)):
                        target.die()
                        g.map.remove_unit(target)
                        for lst in (g.all_units, g.player_units, g.enemy_units):
                            if target in lst:
                                lst.remove(target)
                        if target not in g.dead_units:
                            g.dead_units.append(target)
                        g.combat_log.append({"attacker": unit, "defender": target,
                                             "damage": 0, "message": f"{unit.name} уничтожил {target.name}!"})
                        self._add_combat_effect(unit.x, unit.y, "attack")
                        g.message = f"{unit.name} уничтожил {target.name}!"
                        unit.attacked = True
                        break
                    else:
                        result = resolve_attack(unit, target)
                        if result:
                            g.combat_log.append(result)
                            self._add_combat_effect(unit.x, unit.y, "attack")
                            g.message = f"{unit.name} уничтожил {target.name}!" if not target.is_alive else f"{unit.name} атакует {target.name}"
                            unit.attacked = True
                            break

    # ── detection phase (stub) ───────────────────────────────────────

    def _do_detection_phase(self):
        pass

    # ── ranged combat phase ──────────────────────────────────────────

    def _do_ranged_combat_phase(self):
        self._resolve_artillery_attacks()
        self._resolve_fpv_attacks()

    def _resolve_artillery_attacks(self):
        g = self.game
        for unit in g.all_units:
            if not isinstance(unit, Artillery) or not unit.is_alive:
                continue
            if unit.ammo <= 0:
                unit.pending_target = None
                continue
            target_x, target_y = None, None
            if unit.pending_target:
                target_x, target_y = unit.pending_target
                unit.pending_target = None
                dist = abs(unit.x - target_x) + abs(unit.y - target_y)
                if dist > config.ARTILLERY_BARRAGE_RANGE:
                    target_x, target_y = None, None
            if target_x is None:
                if unit.faction != config.PLAYER:
                    continue
                target = self._find_artillery_target(unit, unit.faction)
                if not target:
                    continue
                target_x, target_y = target.x, target.y
            result = unit.attack_cell(g.map, g.all_units, target_x, target_y, max_range=config.ARTILLERY_BARRAGE_RANGE)
            if result:
                total_dmg, msg, damaged = result
                g.combat_log.append({"attacker": unit, "damage": total_dmg,
                                     "message": f"Артиллерия {unit.name}: {msg}"})
                self._add_projectile_effect(unit.x, unit.y, target_x, target_y)
                self._add_combat_effect(target_x, target_y, "artillery")
                for u, dmg in damaged:
                    if not u.is_alive:
                        g.map.remove_unit(u)
                        for lst in (g.all_units, g.player_units, g.enemy_units):
                            if u in lst:
                                lst.remove(u)
                        if u not in g.dead_units:
                            g.dead_units.append(u)
                g.message = f"Артиллерия: {msg}"

    def _find_artillery_target(self, artillery, faction):
        g = self.game
        enemy_faction = config.ENEMY if faction == config.PLAYER else config.PLAYER
        friendly_units = g.player_units if faction == config.PLAYER else g.enemy_units
        is_player = (faction == config.PLAYER)
        best = None
        best_val = -1
        for u in g.all_units:
            if u.faction != enemy_faction or not u.is_alive:
                continue
            if hasattr(u, 'is_flying') and u.is_flying:
                continue
            dist = abs(artillery.x - u.x) + abs(artillery.y - u.y)
            if dist > artillery.attack_range:
                continue
            cell = g.map.get_cell(u.x, u.y)
            if not cell:
                continue
            if is_player:
                if not g.fog_disabled and not cell.visible:
                    continue
            else:
                spotted = False
                for fu in friendly_units:
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
            if dist > artillery.attack_range:
                continue
            val = 0
            if isinstance(u, Warehouse):
                val = config.ARTILLERY_TARGET_PRIORITY_WAREHOUSE
            elif isinstance(u, SupplyCache):
                val = config.ARTILLERY_TARGET_PRIORITY_CACHE
            elif isinstance(u, Tank):
                val = config.ARTILLERY_TARGET_PRIORITY_TANK
            elif isinstance(u, Infantry):
                val = config.ARTILLERY_TARGET_PRIORITY_INFANTRY
            elif isinstance(u, Artillery):
                val = config.ARTILLERY_TARGET_PRIORITY_ARTILLERY
            elif isinstance(u, (ReconOperator, FPVOperator)):
                val = config.ARTILLERY_TARGET_PRIORITY_OPERATOR
            if val > best_val:
                best_val = val
                best = u
        return best

    def _resolve_fpv_attacks(self):
        g = self.game
        seen = set()
        deduped = []
        for d in g.fpv_drones_in_flight:
            if id(d) not in seen:
                seen.add(id(d))
                deduped.append(d)
        g.fpv_drones_in_flight = deduped

        for drone in list(g.fpv_drones_in_flight):
            if not drone.is_alive:
                self._cleanup_dead_drone(drone)
                continue
            if not drone.target or not drone.target.is_alive:
                drone.die()
                self._cleanup_dead_drone(drone)
                continue
            if drone.reached and not drone.attacked:
                drone.try_attack(g.map, g.combat_log, lambda msg: setattr(g, 'message', msg))
                if not drone.is_alive:
                    self._cleanup_dead_drone(drone)

    def _cleanup_dead_drone(self, drone):
        g = self.game
        if drone in g.fpv_drones_in_flight:
            g.fpv_drones_in_flight.remove(drone)
        g.map.remove_unit(drone)
        for lst in (g.all_units, g.player_units, g.enemy_units):
            if drone in lst:
                lst.remove(drone)

    def _create_fpv_drones(self):
        g = self.game

        def _operator_has_drone_in_flight(op):
            return any(
                d.is_alive and d.operator is op and not d.attacked
                for d in g.fpv_drones_in_flight
            )

        operators = [u for u in g.all_units
                     if isinstance(u, FPVOperator) and u.is_alive
                     and getattr(u, 'auto_mode', False) and u.fpv_stock > 0
                     and not getattr(u, '_fpv_launched_this_turn', False)
                     and not _operator_has_drone_in_flight(u)]

        for unit in operators:
            faction = unit.faction
            enemy_faction = config.ENEMY if faction == config.PLAYER else config.PLAYER
            friendly_units = g.player_units if faction == config.PLAYER else g.enemy_units

            recon_drones = [d for d in g.all_units if isinstance(d, ReconDrone) and d.is_alive and d.faction == faction and not d.jammed]

            priority_target = None
            fallback_target = None

            for enemy in g.all_units:
                if enemy.faction != enemy_faction or not enemy.is_alive:
                    continue
                if isinstance(enemy, (ReconDrone, FPVDrone, Warehouse, SupplyCache)):
                    continue
                cell = g.map.get_cell(enemy.x, enemy.y)
                if not cell:
                    continue
                dist_to_op = abs(enemy.x - unit.x) + abs(enemy.y - unit.y)
                if dist_to_op > config.FPV_OPERATOR_RANGE:
                    continue

                spotted_by_drone = False
                for drone in recon_drones:
                    dist = abs(enemy.x - drone.x) + abs(enemy.y - drone.y)
                    if dist <= drone.vision_range:
                        stealth = g.map._get_stealth(enemy, g.map) + g.map._cell_stealth_bonus(cell.terrain)
                        detect_range = max(0, drone.vision_range - stealth)
                        if dist <= detect_range:
                            spotted_by_drone = True
                            break
                if spotted_by_drone:
                    priority_target = enemy
                    break

                if not fallback_target:
                    spotted_by_unit = False
                    for fu in friendly_units:
                        if not fu.is_alive or fu is unit:
                            continue
                        if isinstance(fu, (Warehouse, SupplyCache)):
                            continue
                        fdist = abs(enemy.x - fu.x) + abs(enemy.y - fu.y)
                        if fdist <= fu.vision_range:
                            spotted_by_unit = True
                            break
                    if spotted_by_unit:
                        fallback_target = enemy

            target = priority_target or fallback_target
            if target:
                if unit.launch_fpv():
                    unit._fpv_launched_this_turn = True
                    fpv = FPVDrone(unit.x, unit.y, faction, target, f"FPV-{unit.name}", operator=unit)
                    g.all_units.append(fpv)
                    friendly_units.append(fpv)
                    g.map.add_unit(fpv, unit.x, unit.y)
                    g.fpv_drones_in_flight.append(fpv)
                    g.message = f"{unit.name} запустил FPV по {target.name}"

    def _is_drone_detected(self, enemy_drone, friendly_drones):
        return any(d.is_alive for d in friendly_drones if abs(d.x - enemy_drone.x) + abs(d.y - enemy_drone.y) <= d.vision_range)

    # ── close combat phase ───────────────────────────────────────────

    def _do_close_combat_phase(self):
        g = self.game
        for unit in g.player_combat_units:
            if not unit.is_alive or not unit.attacked:
                continue
            cell = g.map.get_cell(unit.x, unit.y)
            if not cell:
                continue
            for other in cell.units[:]:
                if other.faction == config.ENEMY and other.is_alive and unit.ammo > 0:
                    resolve_attack(unit, other)

    # ── logistics phase ──────────────────────────────────────────────

    def _do_logistics_phase(self):
        g = self.game
        for op in g.player_units:
            if not isinstance(op, ReconOperator) or not op.is_alive:
                continue
            cell_op = g.map.get_cell(op.x, op.y)
            if cell_op:
                for wh in cell_op.units:
                    if isinstance(wh, Warehouse) and wh.faction == config.PLAYER:
                        if op.batteries < op.max_batteries and wh.batteries > 0:
                            taken = op.load_batteries_from_warehouse(wh)
                            if taken > 0:
                                g.message = f"{op.name} взял {taken} батарей со склада"
            for drone in g.player_units:
                if not isinstance(drone, ReconDrone) or not drone.is_alive:
                    continue
                if drone.battery >= drone.max_battery:
                    continue
                if abs(op.x - drone.x) + abs(op.y - drone.y) > 1:
                    continue
                if op.recharge_drone(drone):
                    g.message = f"{op.name} зарядил {drone.name}"

        for unit in g.all_units:
            if not unit.is_alive:
                continue
            if isinstance(unit, Infantry):
                unit.consume_food(g.turn)
                treated = unit.treat_wounded()
                if treated > 0:
                    g.message = f"{unit.name}: вылечено {treated} раненых"
            elif isinstance(unit, SoldierUnit):
                unit.consume_food()
            elif isinstance(unit, (ReconOperator, FPVOperator, Tank)):
                unit.consume_food()
            elif isinstance(unit, RadarEW):
                unit.consume_food()
            elif isinstance(unit, ReconDrone):
                unit.consume_battery()
                if unit.battery <= 0:
                    unit.die()

        for wh in g.all_units:
            if isinstance(wh, Warehouse) and wh.faction == config.PLAYER and g.turn > 0:
                if g.turn % config.SUPPLY_REINFORCEMENT_INTERVAL == 0:
                    wh.reinforce()
                    g.message = "Склад пополнен из тыла!"

        for truck in g.all_units:
            if not isinstance(truck, SupplyTruck) or not truck.is_alive:
                continue
            route = truck.supply_route
            if not route:
                continue
            origin = route["origin"]
            dest = route["dest"]
            if not origin.is_alive or not dest.is_alive:
                truck.supply_route = None
                g.clear_waypoints(truck)
                g.message = f"{truck.name}: маршрут прерван (склад/погреб уничтожен)"
                continue
            dist_to_origin = abs(truck.x - origin.x) + abs(truck.y - origin.y)
            dist_to_dest = abs(truck.x - dest.x) + abs(truck.y - dest.y)
            if route["state"] == "loading" and dist_to_origin <= 1:
                amt = g._transfer_to_truck(truck, origin)
                if amt > 0:
                    g.message = f"{truck.name} загрузил {amt} припасов с {origin.name}"
                    route["state"] = "traveling_to_dest"
                    avoid = [u for u in g.player_units if u is not truck and u.is_alive and not isinstance(u, (ReconDrone, FPVDrone))]
                    tx, ty = g._find_adjacent(dest, truck)
                    if tx is not None:
                        path = g.map.find_path(truck.x, truck.y, tx, ty, max_cost=99, unit=truck, avoid_units=avoid)
                        if path and len(path) >= 2:
                            g.set_waypoint(truck, path[1:])
                else:
                    g.message = f"{truck.name}: нечего грузить на {origin.name}"
            elif route["state"] == "unloading" and dist_to_dest <= 1:
                amt = g._transfer_from_truck(truck, dest)
                if amt > 0:
                    g.message = f"{truck.name} выгрузил {amt} припасов на {dest.name}"
                    route["state"] = "traveling_to_origin"
                    avoid = [u for u in g.player_units if u is not truck and u.is_alive and not isinstance(u, (ReconDrone, FPVDrone))]
                    tx, ty = g._find_adjacent(origin, truck)
                    if tx is not None:
                        path = g.map.find_path(truck.x, truck.y, tx, ty, max_cost=99, unit=truck, avoid_units=avoid)
                        if path and len(path) >= 2:
                            g.set_waypoint(truck, path[1:])
            elif route["state"] == "traveling_to_dest" and dist_to_dest <= 1:
                amt = g._transfer_from_truck(truck, dest)
                if amt > 0:
                    g.message = f"{truck.name} выгрузил {amt} припасов на {dest.name}"
                route["state"] = "loading"
            elif route["state"] == "traveling_to_origin" and dist_to_origin <= 1:
                route["state"] = "loading"

        for unit in list(g.all_units):
            if not unit.is_alive or not isinstance(unit, (Tank, Infantry)):
                continue
            resupplied = False
            for u in g.all_units:
                if not u.is_alive or not isinstance(u, (SupplyCache, Warehouse)):
                    continue
                if abs(unit.x - u.x) + abs(unit.y - u.y) > 1:
                    continue
                if hasattr(unit, 'ammo') and unit.ammo < unit.max_ammo and hasattr(u, 'ammo') and u.ammo > 0:
                    taken = min(u.ammo, unit.max_ammo - unit.ammo)
                    u.ammo -= taken
                    unit.ammo += taken
                    resupplied = True
                    g.message = f"{unit.name} пополнил боезапас (+{taken})"
                if isinstance(unit, Tank) and hasattr(u, 'fuel') and u.fuel > 0 and unit.fuel < unit.max_fuel:
                    taken = min(u.fuel, unit.max_fuel - unit.fuel)
                    u.fuel -= taken
                    unit.fuel += taken
                    resupplied = True
                    g.message = f"{unit.name} пополнил топливо (+{taken})"
                if isinstance(unit, Infantry) and hasattr(u, 'supplies') and u.supplies > 0:
                    resupplied_food = 0
                    for s in unit.alive_soldiers:
                        if s.food < s.max_food and u.supplies > 0:
                            take = min(2, s.max_food - s.food, u.supplies)
                            s.food += take
                            u.supplies -= take
                            resupplied_food += take
                    if resupplied_food > 0:
                        resupplied = True
                        g.message = f"{unit.name} пополнил еду (+{resupplied_food})"
                if resupplied:
                    return_pos = getattr(unit, '_resupply_return_pos', None)
                    if return_pos and (unit.x != return_pos[0] or unit.y != return_pos[1]):
                        avoid = [v for v in g.player_units if v is not unit and v.is_alive]
                        rx, ry = return_pos
                        ret_path = g.map.find_path(unit.x, unit.y, rx, ry, max_cost=99, unit=unit, avoid_units=avoid)
                        if ret_path and len(ret_path) >= 2:
                            g.set_waypoint(unit, ret_path[1:])
                            g.message += f" → возврат на ({rx},{ry})"
                    else:
                        if unit in g.waypoints:
                            g.clear_waypoints(unit)
                    unit._resupply_return_pos = None

    # ── entrench phase ───────────────────────────────────────────────

    def _do_entrench_phase(self):
        g = self.game
        for unit in list(g.all_units):
            if isinstance(unit, Infantry) and unit.is_alive:
                if unit.building_cache:
                    cache = unit.building_cache
                    if cache.is_alive:
                        cache.build_turns += 1
                        if cache.build_turns >= cache.build_required:
                            cache.build_turns = cache.build_required
                            unit.building_cache = None
                            g.map.remove_unit(unit)
                            unit.x, unit.y = -1, -1
                            unit.die()
                            if unit in g.all_units:
                                g.all_units.remove(unit)
                            if unit in g.player_units:
                                g.player_units.remove(unit)
                            if unit in g.enemy_units:
                                g.enemy_units.remove(unit)
                            cache.garrison += 1
                            g.message = f"{cache.name} построен! Отряд в гарнизоне"
                            continue
                    else:
                        unit.building_cache = None
                if unit.entrenching:
                    cell = g.map.get_cell(unit.x, unit.y)
                    if cell:
                        unit.entrench_step(g.map)
                        if cell.entrenchment >= unit.max_entrenchment:
                            unit.entrenching = False

    # ── enemy turn ───────────────────────────────────────────────────

    def _do_enemy_turn(self):
        g = self.game
        results = g.enemy_controller.take_turn()
        msgs = []
        for result in results:
            g.combat_log.append(result)
            msg = result.get("message", "")
            if result.get("defender") and not result["defender"].is_alive:
                target = result["defender"]
                g.map.remove_unit(target)
                for lst in (g.all_units, g.player_units):
                    if target in lst:
                        lst.remove(target)
                if target not in g.dead_units:
                    g.dead_units.append(target)
                msg += " | Уничтожен!"
            if result.get("attacker") and not result["attacker"].is_alive:
                attacker = result["attacker"]
                g.map.remove_unit(attacker)
                for lst in (g.all_units, g.enemy_units):
                    if attacker in lst:
                        lst.remove(attacker)
                if attacker not in g.dead_units:
                    g.dead_units.append(attacker)
                msg += " | Атакующий уничтожен!"
            msgs.append(msg)
        if msgs:
            g.message = " | ".join(msgs[-2:])

    # ── end turn ─────────────────────────────────────────────────────

    def end_turn(self):
        g = self.game
        g.fpv_launched_this_turn = 0
        for u in g.all_units:
            if isinstance(u, FPVOperator):
                u._fpv_launched_this_turn = False
        if not g.fog_disabled:
            g.reveal_all_enemies = False
        for d in list(g.fpv_drones_in_flight):
            if not d.is_alive or not d.target or not d.target.is_alive:
                d.die()
                self._cleanup_dead_drone(d)

        if g.turn > 0 and g.turn % config.SUPPLY_REINFORCEMENT_INTERVAL == 0:
            for wh in g.player_units:
                if isinstance(wh, Warehouse) and wh.is_alive and wh.faction == config.PLAYER:
                    wh.reinforce()
                    wh.fpv_drones = min(wh.fpv_drones + config.WAREHOUSE_REINFORCE_FPV_DRONES, config.WAREHOUSE_MAX_FPV_DRONES)
            for wh in g.enemy_units:
                if isinstance(wh, Warehouse) and wh.is_alive and wh.faction == config.ENEMY:
                    wh.reinforce()
                    wh.fpv_drones = min(wh.fpv_drones + config.WAREHOUSE_REINFORCE_FPV_DRONES, config.WAREHOUSE_MAX_FPV_DRONES)
            g.message = f"Подкрепление прибыло на склады!"

        self._auto_resupply_from_caches()
        self._process_reinforcements()

        for unit in g.all_units:
            if unit.is_alive:
                if isinstance(unit, Infantry):
                    alive = unit.alive_soldiers
                    hungry = [s for s in alive if s.food <= 0]
                    if hungry and len(hungry) >= len(alive) // config.STARVATION_DEATH_THRESHOLD_DIVISOR:
                        random.choice(hungry).is_alive = False
                        g.combat_log.append({"message": f"{hungry[0].full_name} умер от голода"})
                    if unit.soldiers <= 0:
                        unit.die()
                elif isinstance(unit, SoldierUnit):
                    if unit.soldier.food <= 0:
                        unit.soldier.health = max(0, unit.soldier.health - config.SOLDIER_UNIT_STARVATION_DAMAGE)
                        if unit.soldier.health <= 0:
                            unit.die()
                if not unit.moved:
                    unit.stationary_turns += 1
                else:
                    unit.stationary_turns = 0
                unit.reset_turn()

        for u in list(g.all_units):
            if isinstance(u, SupplyCache) and u.is_alive and u.build_turns >= u.build_required:
                if u.garrison <= 0:
                    if random.random() < config.CACHE_ABANDON_CHANCE:
                        g.message = f"{u.name} заброшен (нет гарнизона)"
                        u.die()
                        g.map.remove_unit(u)
                        g.all_units.remove(u)
                        if u in g.player_units:
                            g.player_units.remove(u)
                        if u not in g.dead_units:
                            g.dead_units.append(u)

        self._update_visibility_for_current_faction()

        dead = [u for u in g.all_units if not u.is_alive]
        for u in dead:
            g.map.remove_unit(u)
            g.all_units.remove(u)
            if u in g.player_units:
                g.player_units.remove(u)
            if u in g.enemy_units:
                g.enemy_units.remove(u)

        player_combat = [u for u in g.player_units if isinstance(u, (Infantry, Tank))]
        enemy_combat = [u for u in g.enemy_units if isinstance(u, (Infantry, Tank))]

        g.turn += 1
        alive = len(player_combat)
        combat_info = ""

        if g.game_mode == "hotseat":
            self._switch_current_player()
        if g.combat_log:
            last = g.combat_log[-1].get("message", "")[:30]
            if last:
                combat_info = " | " + last
        g.message = f"Ход {g.turn}/{g.max_turns}. Своих: {alive}, врагов: {len(enemy_combat)}{combat_info}"

    # ── visibility & hot-seat ────────────────────────────────────────

    def _update_visibility_for_current_faction(self):
        g = self.game
        
        # Если туман отключен читом, делаем все клетки видимыми
        if g.fog_disabled:
            current_faction = g.current_player_faction if g.game_mode == "hotseat" else config.PLAYER
            for y in range(g.map.height):
                for x in range(g.map.width):
                    cell = g.map.get_cell(x, y)
                    if cell:
                        cell.visible = True
                        cell.explored = True
                        if current_faction == config.PLAYER:
                            cell.explored_player = True
                        else:
                            cell.explored_enemy = True
            return
        
        if g.game_mode == "hotseat":
            if g.current_player_faction == config.PLAYER:
                g.map.update_visibility(g.player_units, faction=config.PLAYER)
            else:
                g.map.update_visibility(g.enemy_units, faction=config.ENEMY)
        else:
            g.map.update_visibility(g.player_units, faction=config.PLAYER)

        current_faction = g.current_player_faction if g.game_mode == "hotseat" else config.PLAYER
        for y in range(g.map.height):
            for x in range(g.map.width):
                cell = g.map.get_cell(x, y)
                if cell:
                    if current_faction == config.PLAYER:
                        cell.explored_player = cell.explored_player or cell.visible
                    else:
                        cell.explored_enemy = cell.explored_enemy or cell.visible

    def _switch_current_player(self):
        g = self.game
        if g.current_player_faction == config.PLAYER:
            g.current_player_faction = config.ENEMY
            g.hotseat_switch_message = "Ход Игрока 2 (Красные). Передайте компьютер сопернику и нажмите Enter"
        else:
            g.current_player_faction = config.PLAYER
            g.hotseat_switch_message = "Ход Игрока 1 (Синие). Передайте компьютер сопернику и нажмите Enter"
        g.waiting_for_hotseat_switch = True
        g.message = g.hotseat_switch_message
        g.selected_unit = None
        self._update_visibility_for_current_faction()

    def confirm_hotseat_switch(self):
        g = self.game
        if g.waiting_for_hotseat_switch:
            g.waiting_for_hotseat_switch = False
            g.hotseat_switch_message = ""
            g.message = "Ход Игрока 1 (Синие)" if g.current_player_faction == config.PLAYER else "Ход Игрока 2 (Красные)"
            self._update_visibility_for_current_faction()

    # ── combat effects ───────────────────────────────────────────────

    def _add_combat_effect(self, x, y, effect_type, hits=None):
        g = self.game
        g.combat_effects.append({'x': x, 'y': y, 'type': effect_type, 'timer': config.EFFECT_TIMER_COMBAT})
        if hits:
            for hit in hits[:5]:
                hit_x = hit.get('x', x)
                hit_y = hit.get('y', y)
                if hit.get('ricochet'):
                    g.combat_effects.append({'x': hit_x, 'y': hit_y, 'type': 'ricochet', 'timer': config.EFFECT_TIMER_RICOCHET})
                elif hit.get('explosion'):
                    g.combat_effects.append({'x': hit_x, 'y': hit_y, 'type': 'attack', 'timer': config.EFFECT_TIMER_EXPLOSION})
                elif hit.get('kill'):
                    g.combat_effects.append({'x': hit_x, 'y': hit_y, 'type': 'attack', 'timer': config.EFFECT_TIMER_KILL})

    def _add_projectile_effect(self, src_x, src_y, dst_x, dst_y, effect_type="artillery_shell"):
        self.game.combat_effects.append({
            'x': dst_x, 'y': dst_y, 'src_x': src_x, 'src_y': src_y,
            'type': effect_type, 'timer': config.EFFECT_TIMER_PROJECTILE, 'max_timer': config.EFFECT_TIMER_PROJECTILE
        })

    def _update_combat_effects(self):
        for effect in self.game.combat_effects:
            effect['timer'] -= 1
        self.game.combat_effects = [e for e in self.game.combat_effects if e['timer'] > 0]

    # ── resupply & reinforcements ────────────────────────────────────

    def _auto_resupply_units(self):
        g = self.game
        for unit in g.player_units:
            if not unit.is_alive or unit in g.waypoints:
                continue
            checks = []
            if isinstance(unit, Tank):
                checks = [("crew", "max_crew"), ("ammo", "max_ammo"), ("fuel", "max_fuel")]
            elif isinstance(unit, Infantry):
                checks = [("ammo", "max_ammo"), ("food", "max_food")]
            if not checks:
                continue
            low = False
            for attr, max_attr in checks:
                val = getattr(unit, attr, 1)
                mx = getattr(unit, max_attr, 1)
                if mx > 0 and val / mx < config.AUTO_RESUPPLY_THRESHOLD:
                    low = True
                    break
            if not low:
                continue
            best = None
            best_dist = 999
            for u in g.all_units:
                if not u.is_alive or not isinstance(u, (SupplyCache, Warehouse)):
                    continue
                dist = abs(u.x - unit.x) + abs(u.y - unit.y)
                if dist <= config.AUTO_RESUPPLY_RANGE and dist < best_dist:
                    best = u
                    best_dist = dist
            if best:
                g.message = f"{unit.name}: мало ресурсов — нужен {best.name} ({best_dist} кл.)"

    def _auto_resupply_from_caches(self):
        g = self.game
        for source in g.all_units:
            is_cache = isinstance(source, SupplyCache) and source.is_alive and source.build_turns >= source.build_required
            is_warehouse = isinstance(source, Warehouse) and source.is_alive
            if not is_cache and not is_warehouse:
                continue
            resupply_range = config.CACHE_RESUPPLY_RANGE if is_cache else config.WAREHOUSE_RESUPPLY_RANGE
            for unit in g.all_units:
                if not unit.is_alive or unit.faction != source.faction:
                    continue
                dist = abs(unit.x - source.x) + abs(unit.y - source.y)
                if dist > resupply_range:
                    continue
                if isinstance(unit, Infantry):
                    for s in unit.alive_soldiers:
                        if s.food < s.max_food and source.supplies > 0:
                            take = min(config.RESUPPLY_FOOD_PER_SOLDIER, s.max_food - s.food, source.supplies)
                            s.food += take
                            source.supplies -= take
                    total_ammo = sum(s.ammo for s in unit.alive_soldiers)
                    if total_ammo < unit.soldiers * config.SOLDIER_MAX_AMMO and source.ammo > 0:
                        for s in unit.alive_soldiers:
                            if s.ammo < s.max_ammo and source.ammo > 0:
                                take = min(config.RESUPPLY_AMMO_PER_SOLDIER, s.max_ammo - s.ammo, source.ammo)
                                s.ammo += take
                                source.ammo -= take
                elif isinstance(unit, Tank):
                    if unit.fuel < unit.max_fuel and source.fuel > 0:
                        take = min(config.RESUPPLY_TANK_FUEL, unit.max_fuel - unit.fuel, source.fuel)
                        unit.fuel += take
                        source.fuel -= take
                    if unit.ammo < unit.max_ammo and source.ammo > 0:
                        take = min(3, unit.max_ammo - unit.ammo, source.ammo)
                        unit.ammo += take
                        source.ammo -= take
                    if unit.carry_food < unit.max_carry_food and source.supplies > 0:
                        take = min(config.RESUPPLY_TANK_CARRY_FOOD, unit.max_carry_food - unit.carry_food, source.supplies)
                        unit.carry_food += take
                        source.supplies -= take
                    if unit.crew < unit.max_crew and source.supplies > 0:
                        take = min(config.RESUPPLY_CREW_REINFORCE_COST, unit.max_crew - unit.crew, source.supplies // config.RESUPPLY_CREW_REINFORCE_RATIO)
                        unit.crew += take
                        source.supplies -= take * config.RESUPPLY_CREW_REINFORCE_RATIO
                elif isinstance(unit, (ReconOperator, FPVOperator)):
                    if hasattr(unit, 'batteries') and unit.batteries < unit.max_batteries and source.batteries > 0:
                        take = min(config.RESUPPLY_OPERATOR_BATTERIES, unit.max_batteries - unit.batteries, source.batteries)
                        unit.batteries += take
                        source.batteries -= take
                    if hasattr(unit, 'food') and unit.food < unit.max_food and source.supplies > 0:
                        take = min(config.RESUPPLY_OPERATOR_FOOD, unit.max_food - unit.food, source.supplies)
                        unit.food += take
                        source.supplies -= take
                    if hasattr(unit, 'ammo') and unit.ammo < unit.max_ammo and source.ammo > 0:
                        take = min(config.RESUPPLY_OPERATOR_AMMO, unit.max_ammo - unit.ammo, source.ammo)
                        unit.ammo += take
                        source.ammo -= take
                elif isinstance(unit, Artillery):
                    if unit.ammo < unit.max_ammo and source.ammo > 0:
                        take = min(config.RESUPPLY_ARTILLERY_AMMO, unit.max_ammo - unit.ammo, source.ammo)
                        unit.ammo += take
                        source.ammo -= take
                    for s in unit.alive_soldiers:
                        if s.food < s.max_food and source.supplies > 0:
                            take = min(config.RESUPPLY_ARTILLERY_SOLDIER_FOOD, s.max_food - s.food, source.supplies)
                            s.food += take
                            source.supplies -= take
                elif isinstance(unit, RadarEW):
                    if unit.fuel < unit.max_fuel and source.fuel > 0:
                        take = min(config.RESUPPLY_RADAR_EW_FUEL, unit.max_fuel - unit.fuel, source.fuel)
                        unit.fuel += take
                        source.fuel -= take
                    if unit.food < unit.max_food and source.supplies > 0:
                        take = min(config.RESUPPLY_RADAR_EW_FOOD, unit.max_food - unit.food, source.supplies)
                        unit.food += take
                        source.supplies -= take
                elif isinstance(unit, SupplyTruck):
                    if unit.fuel < unit.max_fuel and source.fuel > 0:
                        take = min(config.RESUPPLY_TRUCK_FUEL, unit.max_fuel - unit.fuel, source.fuel)
                        unit.fuel += take
                        source.fuel -= take

    def _process_reinforcements(self):
        g = self.game
        for key in g.reinforcement_timers:
            g.reinforcement_timers[key] -= 1
        if g.reinforcement_timers['infantry'] <= 0:
            self._spawn_infantry()
            g.reinforcement_timers['infantry'] = config.REINFORCEMENT_INFANTRY_INTERVAL
        if g.reinforcement_timers['tank'] <= 0:
            self._spawn_tank()
            g.reinforcement_timers['tank'] = config.REINFORCEMENT_TANK_INTERVAL
        if g.reinforcement_timers['drone'] <= 0:
            self._spawn_drone()
            g.reinforcement_timers['drone'] = config.REINFORCEMENT_DRONE_INTERVAL
        if g.reinforcement_timers['fpv'] <= 0:
            self._spawn_fpv_operator()
            g.reinforcement_timers['fpv'] = config.REINFORCEMENT_FPV_INTERVAL

    def _spawn_infantry(self):
        g = self.game
        for faction, units, label in [(config.PLAYER, g.player_units, "Подкрепление"), (config.ENEMY, g.enemy_units, "Вражеское подкрепление")]:
            wh_list = [u for u in units if isinstance(u, Warehouse) and u.is_alive]
            if not wh_list:
                continue
            wh = wh_list[0]
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,1)]:
                nx, ny = wh.x + dx, wh.y + dy
                cell = g.map.get_cell(nx, ny)
                if cell and cell.is_walkable and not any(u.x == nx and u.y == ny and u.is_alive for u in g.all_units):
                    inf = Infantry(nx, ny, faction, f"{label} {g.turn}")
                    g.all_units.append(inf)
                    units.append(inf)
                    g.map.add_unit(inf, nx, ny)
                    if faction == config.PLAYER:
                        g.message = "Прибыло подкрепление пехоты!"
                    break

    def _spawn_tank(self):
        g = self.game
        for faction, units in [(config.PLAYER, g.player_units), (config.ENEMY, g.enemy_units)]:
            wh_list = [u for u in units if isinstance(u, Warehouse) and u.is_alive]
            if not wh_list:
                continue
            wh = wh_list[0]
            for dx, dy in [(config.TANK_SPAWN_OFFSET,0), (-config.TANK_SPAWN_OFFSET,0), (0,config.TANK_SPAWN_OFFSET), (0,-config.TANK_SPAWN_OFFSET)]:
                nx, ny = wh.x + dx, wh.y + dy
                cell = g.map.get_cell(nx, ny)
                if cell and cell.is_walkable and not any(u.x == nx and u.y == ny and u.is_alive for u in g.all_units):
                    tank = Tank(nx, ny, faction, f"Танк {g.turn}")
                    g.all_units.append(tank)
                    units.append(tank)
                    g.map.add_unit(tank, nx, ny)
                    if faction == config.PLAYER:
                        g.message = "Прибыл танк!"
                    break

    def _spawn_drone(self):
        g = self.game
        for faction, units in [(config.PLAYER, g.player_units), (config.ENEMY, g.enemy_units)]:
            wh_list = [u for u in units if isinstance(u, Warehouse) and u.is_alive]
            if not wh_list or wh_list[0].batteries < config.DRONE_SPAWN_BATTERY_COST:
                continue
            wh = wh_list[0]
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = wh.x + dx, wh.y + dy
                cell = g.map.get_cell(nx, ny)
                if cell and cell.is_walkable and not any(u.x == nx and u.y == ny and u.is_alive for u in g.all_units):
                    drone = ReconDrone(nx, ny, faction, f"Дрон {g.turn}")
                    g.all_units.append(drone)
                    units.append(drone)
                    g.map.add_unit(drone, nx, ny)
                    wh.batteries -= config.DRONE_SPAWN_BATTERY_COST
                    if faction == config.PLAYER:
                        g.message = "Прибыл разведдрон!"
                    break

    def _spawn_fpv_operator(self):
        g = self.game
        for faction, units in [(config.PLAYER, g.player_units), (config.ENEMY, g.enemy_units)]:
            wh_list = [u for u in units if isinstance(u, Warehouse) and u.is_alive]
            if not wh_list:
                continue
            wh = wh_list[0]
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = wh.x + dx, wh.y + dy
                cell = g.map.get_cell(nx, ny)
                if cell and cell.is_walkable and not any(u.x == nx and u.y == ny and u.is_alive for u in g.all_units):
                    op = FPVOperator(nx, ny, faction, f"FPV {g.turn}")
                    g.all_units.append(op)
                    units.append(op)
                    g.map.add_unit(op, nx, ny)
                    if faction == config.PLAYER:
                        g.message = "Прибыл FPV-расчёт!"
                    break

    def get_reinforcement_info(self):
        g = self.game
        return {k: v for k, v in g.reinforcement_timers.items()}

    # ── artillery commands (called from UI) ──────────────────────────

    def order_artillery_attack(self, target_x, target_y):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, Artillery) or not unit.is_alive:
            g.message = "Выберите артиллерию"
            return
        if unit.ammo <= 0:
            g.message = "Нет снарядов"
            return
        dist = abs(unit.x - target_x) + abs(unit.y - target_y)
        if dist > unit.attack_range:
            g.message = f"Цель вне досягаемости (макс {unit.attack_range} кл.)"
            return
        result = unit.attack_cell(g.map, g.all_units, target_x, target_y)
        if result:
            total_dmg, msg, damaged = result
            g.combat_log.append({"attacker": unit, "damage": total_dmg, "message": f"{unit.name}: {msg}"})
            self._add_projectile_effect(unit.x, unit.y, target_x, target_y)
            self._add_combat_effect(target_x, target_y, "artillery")
            for u, dmg in damaged:
                if not u.is_alive:
                    g.map.remove_unit(u)
                    for lst in (g.all_units, g.player_units, g.enemy_units):
                        if u in lst:
                            lst.remove(u)
                    if u not in g.dead_units:
                        g.dead_units.append(u)
            g.message = f"{unit.name}: {msg}"
        else:
            g.message = f"{unit.name}: промах"
        g.selected_unit = None

    def order_artillery_barrage(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, Artillery) or not unit.is_alive:
            g.message = "Выберите артиллерию"
            return
        if unit.ammo <= 0:
            g.message = "Нет снарядов"
            return
        g.artillery_barrage_mode = unit
        g.message = f"Кликните на клетку для обстрела (дальность {config.ARTILLERY_BARRAGE_RANGE} кл.)"

    def confirm_artillery_barrage(self, target_x, target_y):
        g = self.game
        unit = g.artillery_barrage_mode
        if not unit or not unit.is_alive:
            g.artillery_barrage_mode = None
            return
        dist = abs(unit.x - target_x) + abs(unit.y - target_y)
        barrage_range = config.ARTILLERY_BARRAGE_RANGE
        if dist > barrage_range:
            g.message = f"Цель вне досягаемости (макс {barrage_range} кл.)"
            g.artillery_barrage_mode = None
            return
        unit.pending_target = (target_x, target_y)
        g.message = f"{unit.name}: обстрел ({target_x},{target_y}) на следующем ходу"
        g.artillery_barrage_mode = None
        g.selected_unit = None

    # ── main update ──────────────────────────────────────────────────

    def update(self):
        g = self.game
        if g.phase != config.PHASE_PLANNING:
            g.phase_timer -= 1
            if g.phase_timer <= 0:
                self.advance_phase()
                if g.phase == config.PHASE_PLANNING:
                    g.phase_timer = 0
                else:
                    g.phase_timer = config.PHASE_TIMER_DEFAULT
        self._update_combat_effects()
        g._update_movement_animation()
