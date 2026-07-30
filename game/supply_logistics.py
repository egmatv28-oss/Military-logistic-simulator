from . import config
from .units import (Infantry, Tank, ReconDrone, FPVDrone, SupplyTruck,
                    Warehouse, FPVOperator, ReconOperator, SupplyCache,
                    Artillery, SoldierUnit, RadarEW)
from .resource_transfer import transfer as _rt_transfer, can_accept_resource as _rt_can_accept


class SupplyLogistics:
    """Supply routes, truck loading/unloading, warehouse/cache transfers, waypoints."""

    def __init__(self, game):
        self.game = game

    # ── supply route commands ────────────────────────────────────────

    def order_start_supply_line(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SupplyTruck) or not unit.is_alive:
            g.message = "Выберите грузовик"
            return
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для маршрута"
            return
        g.supply_line_select_mode = unit
        g.message = "Кликните на погреб для назначения маршрута"
        g.selected_unit = None

    def order_assign_supply_dest(self, gx, gy):
        g = self.game
        truck = g.supply_line_select_mode
        if not truck or not truck.is_alive:
            g.supply_line_select_mode = None
            return
        target = None
        for u in g.all_units:
            if not u.is_alive or u.x != gx or u.y != gy or not isinstance(u, SupplyCache):
                continue
            target = u
            break
        if not target:
            g.message = "Кликните по погребу (строению)"
            return
        if target.build_turns < target.build_required:
            g.message = "Погреб ещё строится"
            return
        if target is truck:
            g.message = "Грузовик не может быть погребом"
            return
        origin = None
        best_dist = 999
        for u in g.all_units:
            if not u.is_alive or not isinstance(u, Warehouse) or u.faction != config.PLAYER:
                continue
            dist = abs(u.x - target.x) + abs(u.y - target.y)
            if dist < best_dist:
                best_dist = dist
                origin = u
        if not origin:
            g.message = "Нет склада на карте"
            g.supply_line_select_mode = None
            return
        if origin is target:
            g.message = "Склад и погреб совпадают"
            g.supply_line_select_mode = None
            return
        truck.supply_route = {"origin": origin, "dest": target, "state": "to_origin",
                              "cargo_type": config.CARGO_SUPPLIES}
        self._set_supply_waypoint(truck, origin.x, origin.y)
        g.message = f"Маршрут: {origin.name} -> {target.name}"
        g.supply_line_select_mode = None

    def order_set_origin(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SupplyTruck) or not unit.is_alive:
            g.message = "Выберите грузовик"
            return
        g.origin_select_mode = unit
        g.message = "Кликните на склад или погреб для загрузки"

    def order_set_dest(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SupplyTruck) or not unit.is_alive:
            g.message = "Выберите грузовик"
            return
        g.dest_select_mode = unit
        g.message = "Кликните на погреб для назначения точки доставки"

    def confirm_set_origin(self, gx, gy):
        g = self.game
        truck = g.origin_select_mode
        if not truck or not truck.is_alive:
            g.origin_select_mode = None
            return
        target = None
        for u in g.all_units:
            if not u.is_alive or not isinstance(u, (Warehouse, SupplyCache)):
                continue
            if u.faction != truck.faction or u.x != gx or u.y != gy:
                continue
            target = u
            break
        if not target:
            g.message = "Кликните по складу или погребу"
            return
        if isinstance(target, SupplyCache) and target.build_turns < target.build_required:
            g.message = "Погреб ещё строится"
            return
        truck._route_origin = target
        g.message = f"Точка загрузки: {target.name}"
        g.origin_select_mode = None
        self._try_start_route(truck)

    def confirm_set_dest(self, gx, gy):
        g = self.game
        truck = g.dest_select_mode
        if not truck or not truck.is_alive:
            g.dest_select_mode = None
            return
        target = None
        for u in g.all_units:
            if not u.is_alive or not isinstance(u, SupplyCache) or u.x != gx or u.y != gy:
                continue
            target = u
            break
        if not target:
            g.message = "Кликните по погребу"
            return
        if target.build_turns < target.build_required:
            g.message = "Погреб ещё строится"
            return
        truck._route_dest = target
        g.message = f"Погреб: {target.name}"
        g.dest_select_mode = None
        self._try_start_route(truck)

    def _try_start_route(self, truck):
        g = self.game
        origin = truck._route_origin
        dest = truck._route_dest
        if not origin or not origin.is_alive or not dest or not dest.is_alive:
            return
        truck.supply_route = {"origin": origin, "dest": dest, "state": "to_origin",
                              "cargo_type": config.CARGO_SUPPLIES}
        self._set_supply_waypoint(truck, origin.x, origin.y)
        g.message = f"Маршрут: {origin.name} -> {dest.name}"

    def order_cancel_supply_line(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SupplyTruck) or not unit.is_alive:
            return
        if unit.supply_route:
            unit.supply_route = None
            g.clear_waypoints(unit)
            g.message = "Маршрут отменён"

    def order_deliver_to_unit(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SupplyTruck) or not unit.is_alive:
            g.message = "Выберите грузовик"
            return
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для доставки"
            return
        g.deliver_target_mode = unit
        g.message = "Кликните на юнита для доставки"

    def confirm_deliver_to_unit(self, gx, gy):
        g = self.game
        truck = g.deliver_target_mode
        if not truck or not truck.is_alive:
            g.deliver_target_mode = None
            return
        target = None
        for u in g.all_units:
            if not u.is_alive or u is truck or u.x != gx or u.y != gy or u.faction != config.PLAYER:
                continue
            target = u
            break
        if not target:
            g.message = "Кликните на союзного юнита"
            return
        tx, ty = None, None
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            cx, cy = target.x + dx, target.y + dy
            cell = g.map.get_cell(cx, cy)
            if cell and cell.is_walkable and g._can_occupy(truck, cx, cy):
                tx, ty = cx, cy
                break
        if tx is None:
            g.message = "Нет свободной клетки рядом"
            g.deliver_target_mode = None
            return
        avoid = [u for u in g.player_units if u is not truck and u.is_alive and not isinstance(u, (ReconDrone, FPVDrone))]
        path = g.map.find_path(truck.x, truck.y, tx, ty, max_cost=99, unit=truck, avoid_units=avoid)
        if path and len(path) >= 2:
            g.waypoints[truck] = path[1:]
            truck._delivery_target = target
            g.message = f"{truck.name} -> {target.name} (доставка)"
        else:
            g.message = "Нет пути"
        g.deliver_target_mode = None

    # ── truck load/unload ────────────────────────────────────────────

    def load_truck(self, load_type=None):
        g = self.game
        truck = g.selected_unit
        wh = None
        if truck and isinstance(truck, Warehouse) and truck.faction == config.PLAYER:
            wh = truck
            for dx, dy in config.DIRECTIONS + [(0, 0)]:
                nx, ny = wh.x + dx, wh.y + dy
                cell = g.map.get_cell(nx, ny)
                if not cell:
                    continue
                for u in cell.units:
                    if isinstance(u, SupplyTruck) and u.is_alive:
                        truck = u
                        break
                if truck and truck is not wh:
                    break
            if truck is wh:
                g.message = "Нет грузовика рядом со складом"
                return
        if getattr(truck, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для загрузки"
            return
        elif not truck or not isinstance(truck, SupplyTruck):
            g.message = "Выберите грузовик или склад"
            return
        else:
            for dx, dy in config.DIRECTIONS + [(0, 0)]:
                nx, ny = truck.x + dx, truck.y + dy
                cell = g.map.get_cell(nx, ny)
                if not cell:
                    continue
                for u in cell.units:
                    if isinstance(u, Warehouse) and u.faction == config.PLAYER:
                        wh = u
                        break
                if wh:
                    break
            if not wh:
                g.message = "Грузовик должен быть рядом со складом"
                return
        if load_type is None:
            load_type = truck.current_load_type
        wh_key_map = {config.CARGO_SUPPLIES: 'supplies', config.CARGO_AMMO: 'ammo',
                      config.CARGO_FUEL: 'fuel', config.CARGO_BATTERIES: 'batteries',
                      config.CARGO_FPV_DRONE: 'fpv_drones', config.CARGO_RECON_DRONE: 'recon_drones'}
        wh_attr = wh_key_map.get(load_type)
        if not wh_attr:
            g.message = "Неизвестный тип груза"
            return
        available = getattr(wh, wh_attr, 0)
        if available <= 0:
            g.message = f"На складе нет {config.CARGO_NAMES.get(load_type, load_type).lower()}"
            return
        wpu = config.CARGO_WEIGHT_PER_UNIT.get(load_type, 1)
        max_by_weight = truck.weight_remaining // wpu
        if max_by_weight <= 0:
            g.message = f"Грузовик полон (вес {truck.total_weight}/{truck.max_weight})"
            return
        taken = min(max_by_weight, 10, available)
        truck.cargo[load_type] = truck.cargo.get(load_type, 0) + taken
        setattr(wh, wh_attr, getattr(wh, wh_attr) - taken)
        g.message = f"Загружено {taken} {config.CARGO_NAMES.get(load_type, load_type).lower()} (вес {taken*wpu}кг)"

    def unload_truck(self):
        g = self.game
        truck = g.selected_unit
        if not truck or not isinstance(truck, SupplyTruck):
            g.message = "Выберите грузовик"
            return
        if getattr(truck, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для разгрузки"
            return
        if truck.total_weight <= 0:
            g.message = "Грузовик пуст"
            return
        cell = g.map.get_cell(truck.x, truck.y)
        if not cell:
            return
        targets = [u for u in cell.units if u.faction == truck.faction and u is not truck and u.is_alive]
        if not targets:
            g.message = "На этой клетке нет союзных юнитов"
            return
        total = 0
        for target in targets:
            if isinstance(target, Infantry):
                for s in target.alive_soldiers:
                    if s.food < s.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                        given = truck.unload(config.CARGO_SUPPLIES, s.max_food - s.food)
                        s.food += given
                        total += given
                    if s.ammo < s.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                        given = truck.unload(config.CARGO_AMMO, s.max_ammo - s.ammo)
                        s.ammo += given
                        total += given
            elif isinstance(target, Tank):
                if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                    given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                    target.ammo += given
                    total += given
                if target.fuel < target.max_fuel and truck.cargo.get(config.CARGO_FUEL, 0) > 0:
                    given = truck.unload(config.CARGO_FUEL, target.max_fuel - target.fuel)
                    target.fuel += given
                    total += given
                if target.carry_food < target.max_carry_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                    given = truck.unload(config.CARGO_SUPPLIES, target.max_carry_food - target.carry_food)
                    target.carry_food += given
                    total += given
            elif isinstance(target, ReconOperator):
                if target.batteries < target.max_batteries and truck.cargo.get(config.CARGO_BATTERIES, 0) > 0:
                    given = truck.unload(config.CARGO_BATTERIES, target.max_batteries - target.batteries)
                    target.batteries += given
                    total += given
                if target.food < target.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                    given = truck.unload(config.CARGO_SUPPLIES, target.max_food - target.food)
                    target.food += given
                    total += given
                if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                    given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                    target.ammo += given
                    total += given
            elif isinstance(target, FPVOperator):
                if target.food < target.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                    given = truck.unload(config.CARGO_SUPPLIES, target.max_food - target.food)
                    target.food += given
                    total += given
                if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                    given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                    target.ammo += given
                    total += given
            elif isinstance(target, SupplyTruck):
                if target.fuel < target.max_fuel and truck.cargo.get(config.CARGO_FUEL, 0) > 0:
                    given = truck.unload(config.CARGO_FUEL, target.max_fuel - target.fuel)
                    target.fuel += given
                    total += given
            elif isinstance(target, Artillery):
                if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                    given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                    target.ammo += given
                    total += given
                for s in target.alive_soldiers:
                    if s.food < s.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                        given = truck.unload(config.CARGO_SUPPLIES, s.max_food - s.food)
                        s.food += given
                        total += given
        g.message = f"Пополнено {total} ед. припасов" if total > 0 else "Всё уже заполнено"

    def _auto_unload_to_target(self, truck, target):
        g = self.game
        total = 0
        if isinstance(target, Infantry):
            for s in target.alive_soldiers:
                if s.food < s.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                    given = truck.unload(config.CARGO_SUPPLIES, s.max_food - s.food)
                    s.food += given
                    total += given
                if s.ammo < s.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                    given = truck.unload(config.CARGO_AMMO, s.max_ammo - s.ammo)
                    s.ammo += given
                    total += given
        elif isinstance(target, Tank):
            if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                target.ammo += given
                total += given
            if target.fuel < target.max_fuel and truck.cargo.get(config.CARGO_FUEL, 0) > 0:
                given = truck.unload(config.CARGO_FUEL, target.max_fuel - target.fuel)
                target.fuel += given
                total += given
            if truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0 and target.carry_food < target.max_carry_food:
                given = truck.unload(config.CARGO_SUPPLIES, target.max_carry_food - target.carry_food)
                target.carry_food += given
                total += given
        elif isinstance(target, ReconOperator):
            if target.batteries < target.max_batteries and truck.cargo.get(config.CARGO_BATTERIES, 0) > 0:
                given = truck.unload(config.CARGO_BATTERIES, target.max_batteries - target.batteries)
                target.batteries += given
                total += given
            if target.food < target.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                given = truck.unload(config.CARGO_SUPPLIES, target.max_food - target.food)
                target.food += given
                total += given
            if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                target.ammo += given
                total += given
        elif isinstance(target, FPVOperator):
            if target.food < target.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                given = truck.unload(config.CARGO_SUPPLIES, target.max_food - target.food)
                target.food += given
                total += given
            if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                target.ammo += given
                total += given
        elif isinstance(target, Artillery):
            if target.ammo < target.max_ammo and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
                given = truck.unload(config.CARGO_AMMO, target.max_ammo - target.ammo)
                target.ammo += given
                total += given
            for s in target.alive_soldiers:
                if s.food < s.max_food and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
                    given = truck.unload(config.CARGO_SUPPLIES, s.max_food - s.food)
                    s.food += given
                    total += given

    # ── warehouse/cache transfer ─────────────────────────────────────

    def load_operator_batteries(self):
        g = self.game
        op = g.selected_unit
        if not op or not isinstance(op, ReconOperator):
            g.message = "Выберите оператора дронов"
            return
        if getattr(op, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для зарядки"
            return
        wx, wy = g.map.player_warehouse
        if op.x != wx or op.y != wy:
            g.message = "Оператор должен быть на складе"
            return
        wh = None
        for u in g.player_units:
            if isinstance(u, Warehouse) and u.x == wx and u.y == wy:
                wh = u
                break
        if not wh:
            return
        taken = op.load_batteries_from_warehouse(wh)
        g.message = f"Взято {taken} батарей со склада" if taken > 0 else "Батареи не нужны или складе пуст"

    def transfer_from_cache_to_unit(self, cache, target):
        g = self.game
        if not cache or not isinstance(cache, SupplyCache) or not cache.is_alive:
            g.message = "Нет погреба"
            return False
        if not target or not target.is_alive:
            g.message = "Нет цели"
            return False
        if cache.faction != target.faction:
            g.message = "Можно передавать только союзникам"
            return False
        dist = abs(cache.x - target.x) + abs(cache.y - target.y)
        if dist > 1:
            g.message = "Цель слишком далеко (нужна 1 клетка)"
            return False
        if cache.build_turns < cache.build_required:
            g.message = "Погреб ещё строится"
            return False
        total = 0
        for res in ("food", "ammo", "fuel", "batteries", "fpv"):
            total += _rt_transfer(cache, target, res)
        if total > 0:
            g.message = f"Передано {total} ед. в {target.name}"
            g._add_resource_transfer_effect(cache, target)
        else:
            g.message = "Нечего передавать или цель заполнена"
        return total > 0

    def warehouse_transfer_to_unit_direct(self, target):
        g = self.game
        wh = g.selected_unit
        if not wh or not isinstance(wh, Warehouse) or not wh.is_alive:
            g.message = "Выберите склад"
            return False
        if not target or not target.is_alive:
            g.message = "Нет цели"
            return False
        if wh.faction != target.faction:
            g.message = "Можно передавать только союзникам"
            return False
        dist = abs(wh.x - target.x) + abs(wh.y - target.y)
        if dist > 1:
            g.message = "Цель слишком далеко (нужна 1 клетка)"
            return False
        total = 0
        for res in ("food", "ammo", "fuel", "batteries", "fpv"):
            total += _rt_transfer(wh, target, res)
        if total > 0:
            g.message = f"Передано {total} ед. из {wh.name} в {target.name}"
            g._add_resource_transfer_effect(wh, target)
        else:
            g.message = "Нечего передавать или цель заполнена"
        return total > 0

    def warehouse_transfer_to_unit(self):
        g = self.game
        g.message = "Кликните на юнита рядом со складом"
        g.warehouse_transfer_mode = True

    # ── route processing ─────────────────────────────────────────────

    def process_supply_routes(self):
        g = self.game
        for truck in g.player_units:
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
                continue
            at_origin = abs(truck.x - origin.x) + abs(truck.y - origin.y) <= 1
            at_dest = abs(truck.x - dest.x) + abs(truck.y - dest.y) <= 1
            state = route["state"]
            has_waypoints = bool(g.waypoints.get(truck))

            if state == "to_origin" and at_origin:
                self._truck_load(truck, origin)
                route["state"] = "to_dest"
                self._set_supply_waypoint(truck, dest.x, dest.y)
                g.message = f"{truck.name} загружен, едет в {dest.name}"
            elif state == "to_dest" and at_dest:
                self._truck_unload(truck, dest)
                route["state"] = "to_origin"
                self._set_supply_waypoint(truck, origin.x, origin.y)
                g.message = f"{truck.name} выгружен в {dest.name}, едет обратно"
            elif not has_waypoints and not at_origin and not at_dest:
                if state in ("to_origin", "loading"):
                    self._set_supply_waypoint(truck, origin.x, origin.y)
                    g.message = f"{truck.name}: пересчёт маршрута к {origin.name}"
                elif state in ("to_dest", "loaded"):
                    self._set_supply_waypoint(truck, dest.x, dest.y)
                    g.message = f"{truck.name}: пересчёт маршрута к {dest.name}"
            elif state == "loading" and at_origin:
                self._truck_load(truck, origin)
                route["state"] = "loaded"
                self._set_supply_waypoint(truck, dest.x, dest.y)
                g.message = f"{truck.name} загружен, едет в {dest.name}"
            elif state == "loaded" and at_dest:
                self._truck_unload(truck, dest)
                route["state"] = "loading"
                self._set_supply_waypoint(truck, origin.x, origin.y)
                g.message = f"{truck.name} выгружен в {dest.name}, едет обратно"

    def _truck_load(self, truck, origin):
        wh_key_map = {config.CARGO_SUPPLIES: 'supplies', config.CARGO_AMMO: 'ammo',
                      config.CARGO_FUEL: 'fuel', config.CARGO_BATTERIES: 'batteries',
                      config.CARGO_FPV_DRONE: 'fpv_drones', config.CARGO_RECON_DRONE: 'recon_drones'}
        if truck.auto_mix:
            for ct in SupplyTruck.CARGO_CYCLE:
                wh_attr = wh_key_map.get(ct, ct)
                available = getattr(origin, wh_attr, 0)
                if available <= 0:
                    continue
                want = min(10, available)
                taken = truck.load_by_weight(ct, want)
                if taken > 0:
                    setattr(origin, wh_attr, getattr(origin, wh_attr, 0) - taken)
                    if truck.weight_remaining <= 0:
                        break
        else:
            ct = truck.current_load_type
            wh_attr = wh_key_map.get(ct, ct)
            available = getattr(origin, wh_attr, 0)
            if available > 0:
                taken = truck.load_by_weight(ct, available)
                if taken > 0:
                    setattr(origin, wh_attr, getattr(origin, wh_attr, 0) - taken)

    def _truck_unload(self, truck, dest):
        is_cache = isinstance(dest, SupplyCache)
        wh_key_map = {config.CARGO_SUPPLIES: 'supplies', config.CARGO_AMMO: 'ammo',
                      config.CARGO_FUEL: 'fuel', config.CARGO_BATTERIES: 'batteries',
                      config.CARGO_FPV_DRONE: 'fpv_drones', config.CARGO_RECON_DRONE: 'recon_drones'}
        for ct in SupplyTruck.CARGO_CYCLE:
            available = truck.cargo.get(ct, 0)
            if available <= 0:
                continue
            wh_attr = wh_key_map.get(ct, ct)
            if is_cache:
                if dest.slots_remaining <= 0:
                    break
                mx = getattr(dest, f"max_{wh_attr}", 999999)
                cur = getattr(dest, wh_attr, 0)
                space = mx - cur
                if space <= 0:
                    continue
                give = min(available, space, dest.slots_remaining)
            else:
                mx = getattr(dest, f"max_{wh_attr}", 999999)
                cur = getattr(dest, wh_attr, 0)
                give = min(available, mx - cur)
            given = truck.unload(ct, give)
            if given > 0:
                setattr(dest, wh_attr, getattr(dest, wh_attr, 0) + given)

    def _set_supply_waypoint(self, truck, tx, ty):
        g = self.game
        avoid = [u for u in g.player_units if u is not truck and u.is_alive and not isinstance(u, (SupplyCache, Warehouse, ReconDrone, FPVDrone))]
        target_unit = None
        for u in g.all_units:
            if u.x == tx and u.y == ty and u.is_alive and u is not truck:
                target_unit = u
                break
        if target_unit:
            best = None
            best_dist = 999
            for nx, ny in g.map.get_neighbors(tx, ty, unit=truck):
                cell = g.map.get_cell(nx, ny)
                if not cell or not cell.is_walkable:
                    continue
                if any(u is not truck and u.x == nx and u.y == ny and u.is_alive for u in g.all_units):
                    continue
                dist = abs(truck.x - nx) + abs(truck.y - ny)
                if dist < best_dist:
                    best_dist = dist
                    best = (nx, ny)
            if best:
                path = g.map.find_path(truck.x, truck.y, best[0], best[1], max_cost=99, unit=truck, avoid_units=avoid)
                if path and len(path) >= 2:
                    g.waypoints[truck] = path[1:]
                    return
        path = g.map.find_path(truck.x, truck.y, tx, ty, max_cost=99, unit=truck, avoid_units=avoid)
        if path and len(path) >= 2:
            g.waypoints[truck] = path[1:]

    # ── transfer helpers ─────────────────────────────────────────────

    def transfer_to_truck(self, truck, source):
        total = 0
        for ct in SupplyTruck.CARGO_CYCLE:
            available = getattr(source, ct, 0)
            if available <= 0:
                continue
            max_take = min(available, 20)
            taken = truck.load_by_weight(ct, max_take)
            if taken > 0:
                setattr(source, ct, getattr(source, ct, 0) - taken)
                total += taken
                if truck.weight_remaining <= 0:
                    break
        return total

    def transfer_from_truck(self, truck, dest):
        total = 0
        for ct in SupplyTruck.CARGO_CYCLE:
            available = truck.cargo.get(ct, 0)
            if available <= 0:
                continue
            max_give = min(available, 20, getattr(dest, f"max_{ct}", 999999) - getattr(dest, ct, 0))
            if max_give > 0:
                truck.cargo[ct] -= max_give
                setattr(dest, ct, getattr(dest, ct, 0) + max_give)
                total += max_give
        return total

    # ── waypoint management ──────────────────────────────────────────

    def set_waypoint_destination(self, unit, tx, ty):
        g = self.game
        if not unit or not unit.is_alive:
            return False
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для перемещения"
            return False
        cell = g.map.get_cell(tx, ty)
        if not cell or not cell.is_walkable:
            g.message = "Непроходимая местность"
            return False
        if isinstance(unit, SoldierUnit):
            avoid = []
        else:
            avoid = [u for u in g.player_units if u is not unit and u.is_alive and not isinstance(u, (ReconDrone, FPVDrone))]
        path = g.map.find_path(unit.x, unit.y, tx, ty, max_cost=99, unit=unit, avoid_units=avoid)
        if not path or len(path) < 2:
            g.message = "Нет пути"
            return False
        g.waypoints[unit] = path[1:]
        if isinstance(unit, SoldierUnit):
            unit.target_x = tx
            unit.target_y = ty
        g.message = f"{unit.name} -> ({tx}, {ty}), {len(path)-1} шагов"
        return True

    def set_waypoint(self, unit, path_nodes):
        self.game.waypoints[unit] = path_nodes

    def clear_waypoints(self, unit):
        self.game.waypoints.pop(unit, None)

    def _find_adjacent(self, target, mover):
        g = self.game
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            cx, cy = target.x + dx, target.y + dy
            cell = g.map.get_cell(cx, cy)
            if cell and cell.is_walkable and g._can_occupy(mover, cx, cy):
                return cx, cy
        return None, None

    def _can_occupy(self, unit, x, y):
        g = self.game
        cell = g.map.get_cell(x, y)
        if not cell:
            return False
        if isinstance(unit, (ReconDrone, FPVDrone)):
            return True
        if not cell.is_walkable:
            return False
        if isinstance(unit, SoldierUnit):
            return True
        for u in g.all_units:
            if u is not unit and u.x == x and u.y == y and u.is_alive:
                if isinstance(u, (ReconDrone, FPVDrone)):
                    continue
                return False
        return True

    # ── waypoint processing ──────────────────────────────────────────

    def process_waypoints(self):
        g = self.game
        current_faction = g.current_player_faction if g.game_mode == "hotseat" else config.PLAYER
        for unit in list(g.waypoints.keys()):
            if not unit.is_alive:
                g.waypoints.pop(unit, None)
                continue
            # Не удаляем waypoints если юнит уже двигался - они нужны для следующего хода
            if unit.moved:
                continue
            if getattr(unit, 'is_understaffed', False):
                g.waypoints.pop(unit, None)
                continue
            if g.game_mode == "hotseat" and unit.faction != current_faction:
                continue
            wps = g.waypoints.get(unit)
            if not wps:
                g.waypoints.pop(unit, None)
                continue

            max_move = g.get_unit_max_move(unit)
            max_steps = g.get_unit_max_steps(unit)
            move_points_left = max_move
            steps_taken = 0
            remaining = wps[:]
            anim_path = []

            while remaining and move_points_left > 0 and steps_taken < max_steps:
                nx, ny = remaining[0]
                if not self._can_occupy(unit, nx, ny):
                    dest = wps[-1]
                    if isinstance(unit, SoldierUnit):
                        avoid = []
                    else:
                        avoid = [u for u in g.player_units if u is not unit and u.is_alive and not isinstance(u, (ReconDrone, FPVDrone))]
                    new_path = g.map.find_path(unit.x, unit.y, dest[0], dest[1], max_cost=99, unit=unit, avoid_units=avoid)
                    if new_path and len(new_path) >= 2:
                        remaining = new_path[1:]
                        nx, ny = remaining[0]
                        if not self._can_occupy(unit, nx, ny):
                            break
                    else:
                        break
                cell = g.map.get_cell(nx, ny)
                move_cost = 1
                if cell and hasattr(unit, 'get_movement_cost'):
                    move_cost = unit.get_movement_cost(cell.terrain)
                if move_points_left < move_cost:
                    break
                if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)) and unit.fuel <= 0:
                    break
                anim_path.append((nx, ny))
                move_points_left -= move_cost
                steps_taken += 1
                if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)):
                    unit.fuel = max(0, unit.fuel - move_cost)
                if isinstance(unit, ReconDrone):
                    unit.consume_battery()
                    g._update_visibility_for_current_faction()
                remaining = remaining[1:]

            if not anim_path:
                continue

            unit.moved = True
            if isinstance(unit, Infantry):
                unit.entrenching = False
            if isinstance(unit, ReconDrone):
                unit.consume_battery()
            if isinstance(unit, SoldierUnit):
                unit.soldier.morale = max(0, unit.soldier.morale - 3)
                if unit.soldier.morale <= 0:
                    unit.die()
                    g.map.remove_unit(unit)
                    for lst in (g.all_units, g.player_units):
                        if unit in lst:
                            lst.remove(unit)
                    if unit not in g.dead_units:
                        g.dead_units.append(unit)
                    g.waypoints.pop(unit, None)
                    msg = f"{unit.soldier.full_name} дезертировал — мораль упала!"
                    g.combat_log.append({"message": msg})
                    g.message = msg
                    continue

            def on_anim_complete(u=unit, rem=remaining):
                g.waypoints[u] = rem
                if not rem:
                    g.waypoints.pop(u, None)
                    if isinstance(u, SoldierUnit):
                        u.target_x = None
                        u.target_y = None
                    g.message = f"{u.name} достиг цели!"
                    if isinstance(u, SupplyTruck) and hasattr(u, '_delivery_target') and u._delivery_target:
                        target = u._delivery_target
                        if target.is_alive:
                            self._auto_unload_to_target(u, target)
                        u._delivery_target = None
                    if isinstance(u, SoldierUnit) and hasattr(u, '_join_target') and u._join_target:
                        target = u._join_target
                        u._join_target = None
                        dx = abs(u.x - target.x)
                        dy = abs(u.y - target.y)
                        if max(dx, dy) <= 1:
                            if target.add_soldier(u.soldier):
                                g.map.remove_unit(u)
                                for lst in (g.all_units, g.player_units):
                                    if u in lst:
                                        lst.remove(u)
                                g.message = f"{u.soldier.full_name} присоединился к {target.name}"

            g._queue_movement_animation(unit, anim_path, on_anim_complete)
