import random
from . import config
from .units import (Infantry, Tank, ReconDrone, FPVDrone, SupplyTruck,
                    Warehouse, FPVOperator, ReconOperator, SupplyCache,
                    SoldierUnit, RadarEW)
from .combat import resolve_attack, resolve_fpv_strike
from .resource_transfer import transfer as _rt_transfer, can_accept_resource as _rt_can_accept


class ActionManager:
    """Player action commands: move, attack, entrench, build, transfer, squad management."""

    def __init__(self, game):
        self.game = game

    # ── unit selection ───────────────────────────────────────────────

    def select_unit(self, unit):
        g = self.game
        current_units = g.player_units if g.game_mode != "hotseat" or g.current_player_faction == config.PLAYER else g.enemy_units
        if unit in current_units and unit.is_alive:
            g.selected_unit = unit
            # Сбрасываем все режимы взаимодействия при выборе юнита
            g.transfer_mode = False
            g.transfer_source = None
            g.transfer_resource = None
            g.cargo_transfer_mode = False
            g.cargo_transfer_truck = None
            g.cargo_transfer_type = None
            g.cargo_transfer_source = None
            g.cargo_transfer_target = None
            g.soldier_management_mode = False
            g.selected_soldier_idx = None
            g.soldier_source_unit = None
            g.soldier_transfer_mode = False
            g.soldier_transfer_target = None
            g.soldier_detail_idx = None
            g.origin_select_mode = None
            g.dest_select_mode = None
            g.supply_line_select_mode = None
            g.deliver_target_mode = None
            g.artillery_barrage_mode = None
            g.join_move_mode = False
            g.moving_warehouse = False
            g.pinned_cell = None

    def select_unit_at(self, x, y):
        g = self.game
        cell = g.map.get_cell(x, y)
        if not cell:
            return
        current_faction = g.current_player_faction if g.game_mode == "hotseat" else config.PLAYER
        for u in cell.units:
            if u.faction == current_faction and u.is_alive:
                g.selected_unit = u
                # Сбрасываем все режимы взаимодействия при выборе юнита
                g.transfer_mode = False
                g.transfer_source = None
                g.transfer_resource = None
                g.cargo_transfer_mode = False
                g.cargo_transfer_truck = None
                g.cargo_transfer_type = None
                g.cargo_transfer_source = None
                g.cargo_transfer_target = None
                g.soldier_management_mode = False
                g.selected_soldier_idx = None
                g.soldier_source_unit = None
                g.soldier_transfer_mode = False
                g.soldier_transfer_target = None
                g.soldier_detail_idx = None
                g.origin_select_mode = None
                g.dest_select_mode = None
                g.supply_line_select_mode = None
                g.deliver_target_mode = None
                g.artillery_barrage_mode = None
                g.join_move_mode = False
                g.moving_warehouse = False
                g.pinned_cell = None
                return

    # ── movement ─────────────────────────────────────────────────────

    def move_selected_unit(self, tx, ty):
        g = self.game
        unit = g.selected_unit
        if not unit or not unit.is_alive or unit.moved:
            return False
        if isinstance(unit, (SupplyCache, Warehouse)):
            g.message = "Этот объект не двигаться"
            return False
        if g.is_animating():
            g.message = "Подождите завершения анимации..."
            return False
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для перемещения"
            return False
        if hasattr(unit, 'jammed') and unit.jammed:
            g.message = "Нет связи с оператором! Дрон неуправляем"
            return False
        if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)) and unit.fuel <= 0:
            g.message = "Нет топлива!"
            return False

        cell = g.map.get_cell(tx, ty)
        if not cell:
            g.message = "Непроходимая местность"
            return False
        if not isinstance(unit, ReconDrone) and not cell.is_walkable:
            g.message = "Непроходимая местность"
            return False

        max_move = g.get_unit_max_move(unit)
        max_steps = g.get_unit_max_steps(unit)

        path = g.map.find_path(unit.x, unit.y, tx, ty, max_cost=max_move, unit=unit)
        if not path or len(path) < 2:
            dist = g.map.distance(unit.x, unit.y, tx, ty)
            if dist > 1:
                result = g.set_waypoint_destination(unit, tx, ty)
                if result:
                    g.selected_unit = None
                return result
            g.message = "Нет пути"
            return False

        target_units = g.map.get_units_at(tx, ty)
        for u in target_units:
            if u.faction == config.PLAYER and u is not unit and not isinstance(u, Warehouse) and not u.moved:
                g.message = "Клетка занята"
                return False

        move_points_left = max_move
        anim_path = []
        for i in range(1, len(path)):
            if len(anim_path) >= max_steps:
                break
            nx, ny = path[i]
            cell = g.map.get_cell(nx, ny)
            if not cell:
                break
            move_cost = 1
            if hasattr(unit, 'get_movement_cost'):
                move_cost = unit.get_movement_cost(cell.terrain)
            if move_points_left < move_cost:
                break
            anim_path.append((nx, ny))
            move_points_left -= move_cost
            if hasattr(unit, 'fuel') and isinstance(unit, (Tank, SupplyTruck, RadarEW)):
                unit.fuel = max(0, unit.fuel - move_cost)
            if isinstance(unit, ReconDrone):
                unit.consume_battery()

        if not anim_path:
            g.message = f"{unit.name}: нет пути"
            return False

        if len(anim_path) < len(path) - 1:
            last_anim = anim_path[-1]
            remaining_start = path.index(last_anim) + 1
            remaining_path = path[remaining_start:]
            if remaining_path:
                g.waypoints[unit] = remaining_path

        def on_anim_complete():
            unit.moved = True
            if isinstance(unit, Infantry):
                if unit.entrenching:
                    unit.entrenching = False
                if unit.building_cache:
                    unit.building_cache = None
                    g.message = "Строительство погреба прервано"
            if isinstance(unit, ReconDrone):
                has_operator = False
                for op in g.all_units:
                    if isinstance(op, ReconOperator) and op.is_alive and op.faction == unit.faction:
                        op_dist = abs(op.x - unit.x) + abs(op.y - unit.y)
                        if op_dist <= config.RADAR_OPERATOR_RANGE:
                            has_operator = True
                            break
                if not has_operator or unit.battery <= 0:
                    g.message = f"{unit.name}: потеря связи / нет батареи"
            g.message = f"{unit.name} -> ({unit.x},{unit.y}), {len(anim_path)} шаг(ов)"
            g.selected_unit = None

        g._start_unit_animation(unit, anim_path, on_anim_complete)
        g.message = f"{unit.name} идёт..."
        return True

    # ── cargo transfer ───────────────────────────────────────────────

    def order_transfer_cargo(self, target_unit=None):
        g = self.game
        source = g.selected_unit
        if not source or not source.is_alive:
            g.message = "Выберите юнит-источник"
            return False
        if target_unit is None:
            target_unit = self._find_nearest_cargo_target(source)
        if not target_unit or not target_unit.is_alive:
            g.message = "Нет цели для передачи"
            return False
        if source.faction != target_unit.faction:
            g.message = "Можно передавать только союзникам"
            return False
        dist = abs(source.x - target_unit.x) + abs(source.y - target_unit.y)
        if dist > 1:
            g.message = "Цель слишком далеко (нужна соседняя клетка)"
            return False
        transferred = g._do_cargo_transfer(source, target_unit)
        if transferred > 0:
            g.message = f"Передано {transferred} ед. груза в {target_unit.name}"
            g.selected_unit = None
            return True
        else:
            g.message = "Нечего передавать или цель заполнена"
            return False

    def _find_nearest_cargo_target(self, source):
        g = self.game
        best_target = None
        best_dist = 999
        for unit in g.all_units:
            if not unit.is_alive or unit is source or unit.faction != source.faction:
                continue
            if isinstance(unit, (ReconDrone, FPVDrone)):
                continue
            dist = abs(source.x - unit.x) + abs(source.y - unit.y)
            if dist <= 1 and dist < best_dist:
                if g._can_accept_cargo(unit):
                    best_target = unit
                    best_dist = dist
        return best_target

    def transfer_resource_by_type(self, source, target, res_type):
        g = self.game
        if not source or not source.is_alive:
            return 0
        if not target or not target.is_alive:
            return 0
        if source.faction != target.faction:
            return 0
        dist = abs(source.x - target.x) + abs(source.y - target.y)
        if dist > 1:
            return 0
        transferred = _rt_transfer(source, target, res_type)
        if transferred > 0:
            g._add_resource_transfer_effect(source, target)
        return transferred

    def _can_accept_cargo(self, unit):
        for res in ("food", "ammo", "fuel", "batteries", "fpv"):
            if _rt_can_accept(unit, res):
                return True
        return False

    def _do_cargo_transfer(self, source, target):
        total = 0
        for res in ("food", "ammo", "fuel", "batteries", "fpv"):
            total += _rt_transfer(source, target, res)
        return total

    # ── resource transfer mode ───────────────────────────────────────

    def start_transfer_mode(self, resource_type):
        g = self.game
        unit = g.selected_unit
        if not unit or not unit.is_alive:
            return
        has_resource = False
        if resource_type == "food":
            if isinstance(unit, Infantry):
                has_resource = any(s.food > 0 for s in unit.alive_soldiers)
            elif isinstance(unit, Tank):
                has_resource = unit.carry_food > 0
            elif isinstance(unit, SoldierUnit):
                has_resource = unit.soldier.food > 0
            elif isinstance(unit, (Warehouse, SupplyCache)):
                has_resource = unit.supplies > 0
            elif isinstance(unit, (ReconOperator, FPVOperator)):
                has_resource = unit.food > 0
        elif resource_type == "ammo":
            if isinstance(unit, Infantry):
                has_resource = any(s.ammo > 0 for s in unit.alive_soldiers)
            elif isinstance(unit, Tank):
                has_resource = unit.ammo > 0
            elif isinstance(unit, SoldierUnit):
                has_resource = unit.soldier.ammo > 0
            elif isinstance(unit, (Warehouse, SupplyCache)):
                has_resource = unit.ammo > 0
            elif isinstance(unit, (ReconOperator, FPVOperator)):
                has_resource = unit.ammo > 0
        elif resource_type == "fuel":
            if isinstance(unit, Tank):
                has_resource = unit.fuel > 0
            elif isinstance(unit, (Warehouse, SupplyCache)):
                has_resource = unit.fuel > 0
        elif resource_type == "batteries":
            if isinstance(unit, ReconOperator):
                has_resource = unit.batteries > 0
            elif isinstance(unit, (Warehouse, SupplyCache)):
                has_resource = unit.batteries > 0
        elif resource_type == "fpv":
            if isinstance(unit, FPVOperator):
                has_resource = unit.fpv_stock > 0
            elif isinstance(unit, (Warehouse, SupplyCache)):
                has_resource = unit.fpv_drones > 0
        if not has_resource:
            g.message = "Нет ресурса для передачи"
            return
        g.transfer_mode = True
        g.transfer_source = unit
        g.transfer_resource = resource_type
        res_names = {"food": "еды", "ammo": "боеприпасов", "fuel": "топлива",
                     "batteries": "батарей", "fpv": "FPV"}
        g.message = f"Кликните на юнита для передачи {res_names.get(resource_type, resource_type)} (1 клетка)"

    def confirm_transfer_to_target(self, target):
        g = self.game
        if not g.transfer_mode or not g.transfer_source:
            return False
        source = g.transfer_source
        res_type = g.transfer_resource
        if not source or not source.is_alive:
            g.cancel_transfer_mode()
            return False
        if not target or not target.is_alive:
            g.message = "Нет цели"
            return False
        if source is target:
            g.message = "Нельзя передать самому себе"
            return False
        if source.faction != target.faction:
            g.message = "Можно передавать только союзникам"
            return False
        dist = abs(source.x - target.x) + abs(source.y - target.y)
        if dist > 1:
            g.message = "Цель слишком далеко (нужна 1 клетка)"
            return False
        transferred = _rt_transfer(source, target, res_type)
        if transferred > 0:
            res_names = {"food": "еды", "ammo": "боеприпасов", "fuel": "топлива",
                         "batteries": "батарей", "fpv": "FPV"}
            g.message = f"Передано {transferred} ед. {res_names.get(res_type, res_type)} → {target.name}"
            g._add_resource_transfer_effect(source, target)
        else:
            g.message = "Нечего передавать или цель заполнена"
        g.cancel_transfer_mode()
        return transferred > 0

    def cancel_transfer_mode(self):
        g = self.game
        g.transfer_mode = False
        g.transfer_source = None
        g.transfer_resource = None

    # ── entrench & build ─────────────────────────────────────────────

    def order_entrench(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, Infantry) or not unit.is_alive:
            g.message = "Только пехота может окапываться"
            return
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно людей для окапывания"
            return
        if unit.entrenching:
            g.message = "Уже окапывается"
            return
        unit.entrenching = True
        g.message = f"{unit.name} начал окапываться"
        g.selected_unit = None

    def order_build_cache(self):
        g = self.game
        if g.phase != config.PHASE_PLANNING:
            g.message = "Только в фазе планирования"
            return
        unit = g.selected_unit
        if not unit or not isinstance(unit, Infantry) or not unit.is_alive:
            g.message = "Только пехота может строить погреб"
            return
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно людей для строительства"
            return
        if unit.building_cache:
            g.message = "Уже строит погреб"
            return
        cell = g.map.get_cell(unit.x, unit.y)
        if not cell or not cell.is_walkable:
            g.message = "Нельзя построить здесь"
            return
        for u in g.all_units:
            if isinstance(u, SupplyCache) and u.is_alive and abs(u.x - unit.x) + abs(u.y - unit.y) <= config.CACHE_MIN_DISTANCE:
                g.message = "Слишком близко к другому погребу"
                return
        suffix = unit.name.split()[-1]
        cache = SupplyCache(unit.x, unit.y, config.PLAYER, f"Погреб {suffix}")
        unit.building_cache = cache
        g.map.add_unit(cache, cache.x, cache.y)
        g.all_units.append(cache)
        g.player_units.append(cache)
        g.message = f"{unit.name} начал строить погреб (5 ходов)"
        g.selected_unit = None

    # ── squad management ─────────────────────────────────────────────

    def order_form_squad(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SoldierUnit) or not unit.is_alive:
            g.message = "Выберите одиночного бойца"
            return False
        for other in g.all_units:
            if not other.is_alive or other is unit or not isinstance(other, SoldierUnit):
                continue
            if other.faction != unit.faction:
                continue
            dist = abs(unit.x - other.x) + abs(unit.y - other.y)
            if dist > 1:
                continue
            soldiers = [unit.soldier, other.soldier]
            new_inf = Infantry(unit.x, unit.y, unit.faction, f"Отряд {unit.soldier.surname}", soldiers=soldiers)
            g.map.remove_unit(unit)
            g.map.remove_unit(other)
            for lst in (g.all_units, g.player_units):
                for u in (unit, other):
                    if u in lst:
                        lst.remove(u)
            g.all_units.append(new_inf)
            g.player_units.append(new_inf)
            g.map.add_unit(new_inf, unit.x, unit.y)
            g.message = f"Создан {new_inf.name} из {len(soldiers)} бойцов"
            g.selected_unit = None
            return True
        g.message = "Нет рядом одиночного бойца для объединения"
        return False

    def order_join_squad(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SoldierUnit) or not unit.is_alive:
            g.message = "Выберите одиночного бойца"
            return False
        best_target = None
        best_dist = 999
        for other in g.all_units:
            if not other.is_alive or other is unit or not isinstance(other, Infantry):
                continue
            if other.faction != unit.faction or len(other.alive_soldiers) >= other.max_soldiers:
                continue
            dist = abs(unit.x - other.x) + abs(unit.y - other.y)
            if dist <= 1 and dist < best_dist:
                best_target = other
                best_dist = dist
        if not best_target:
            g.message = "Нет отряда рядом для присоединения"
            return False
        if best_target.add_soldier(unit.soldier):
            g.map.remove_unit(unit)
            for lst in (g.all_units, g.player_units):
                if unit in lst:
                    lst.remove(unit)
            g.message = f"{unit.soldier.full_name} присоединился к {best_target.name}"
            g.selected_unit = None
            return True
        g.message = "Отряд полон"
        return False

    def order_join_squad_move(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SoldierUnit) or not unit.is_alive:
            g.message = "Выберите одиночного бойца"
            return False
        if g.phase != config.PHASE_PLANNING:
            g.message = "Только в фазе планирования"
            return False
        g.join_move_mode = True
        g.message = "Кликните на отряд для присоединения"
        return True

    def execute_join_squad_move(self, target):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SoldierUnit) or not unit.is_alive:
            return False
        if not target or not target.is_alive or not isinstance(target, Infantry):
            g.message = "Неверная цель"
            return False
        if target.faction != unit.faction:
            g.message = "Нельзя присоединиться к вражескому отряду"
            return False
        if len(target.alive_soldiers) >= target.max_soldiers:
            g.message = "Отряд полон"
            return False
        dx = abs(unit.x - target.x)
        dy = abs(unit.y - target.y)
        if max(dx, dy) <= 1:
            if target.add_soldier(unit.soldier):
                g.map.remove_unit(unit)
                for lst in (g.all_units, g.player_units):
                    if unit in lst:
                        lst.remove(unit)
                g.message = f"{unit.soldier.full_name} присоединился к {target.name}"
                g.selected_unit = None
                g.join_move_mode = False
                return True
            g.message = "Отряд полон"
            return False
        dx = target.x - unit.x
        dy = target.y - unit.y
        if abs(dx) >= abs(dy):
            nx = unit.x + (1 if dx > 0 else -1)
            ny = unit.y
        else:
            nx = unit.x
            ny = unit.y + (1 if dy > 0 else -1)
        g.waypoints[unit] = [(nx, ny)]
        unit._join_target = target
        g.message = f"{unit.soldier.short_name} идёт к {target.name}"
        g.join_move_mode = False
        return True

    def order_load_single_to_truck(self):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, SoldierUnit) or not unit.is_alive:
            g.message = "Выберите одиночного бойца"
            return False
        cell = g.map.get_cell(unit.x, unit.y)
        if not cell:
            g.message = "Нет грузовика"
            return False
        truck = None
        for u in cell.units:
            if isinstance(u, SupplyTruck) and u.is_alive and u.faction == unit.faction:
                truck = u
                break
        if not truck:
            g.message = "Нет грузовика на этой клетке"
            return False
        if len(truck.alive_soldiers) >= truck.max_soldiers:
            g.message = "Грузовик полон"
            return False
        truck.add_soldier(unit.soldier)
        g.map.remove_unit(unit)
        for lst in (g.all_units, g.player_units):
            if unit in lst:
                lst.remove(unit)
        g.message = f"{unit.soldier.full_name} погружен в {truck.name}"
        g.selected_unit = None
        return True

    # ── soldier management ───────────────────────────────────────────

    def enter_soldier_management(self, unit):
        g = self.game
        if not hasattr(unit, 'soldiers_list') or not unit.is_alive:
            return
        g.soldier_management_mode = True
        g.soldier_source_unit = unit
        g.selected_soldier_idx = None
        g.soldier_detail_idx = None
        g.soldier_transfer_mode = False
        g.soldier_transfer_target = None
        g.message = f"Управление составом {unit.name}. Кликните на солдата для просмотра"

    def exit_soldier_management(self):
        g = self.game
        g.soldier_management_mode = False
        g.soldier_source_unit = None
        g.selected_soldier_idx = None
        g.soldier_detail_idx = None
        g.soldier_transfer_mode = False
        g.soldier_transfer_target = None
        g.message = ""

    def select_soldier_for_transfer(self, idx):
        g = self.game
        if not g.soldier_management_mode or not g.soldier_source_unit:
            return
        soldiers = g.soldier_source_unit.alive_soldiers
        if idx < 0 or idx >= len(soldiers):
            return
        g.selected_soldier_idx = idx
        g.soldier_transfer_mode = True
        g.soldier_detail_idx = None
        g.soldier_transfer_target = None
        soldier = soldiers[idx]
        g.message = f"Выбран {soldier.full_name}. Кликните на другой отряд для перевода (ESC-отмена)"

    def confirm_transfer_soldier(self, target_unit):
        g = self.game
        if target_unit is not None and not g.soldier_transfer_mode:
            return False
        if not g.soldier_source_unit or g.selected_soldier_idx is None:
            return False
        soldiers = g.soldier_source_unit.alive_soldiers
        if g.selected_soldier_idx >= len(soldiers):
            g.message = "Солдат уже не в отряде"
            g.selected_soldier_idx = None
            g.soldier_transfer_mode = False
            g.soldier_detail_idx = None
            return False
        soldier = soldiers[g.selected_soldier_idx]
        if g.soldier_source_unit.remove_soldier(soldier):
            sx, sy = g.soldier_source_unit.x, g.soldier_source_unit.y
            spawn_x, spawn_y = sx, sy
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                nx, ny = sx + dx, sy + dy
                cell = g.map.get_cell(nx, ny)
                if cell and cell.is_walkable:
                    spawn_x, spawn_y = nx, ny
                    break
            su = SoldierUnit(spawn_x, spawn_y, g.soldier_source_unit.faction, soldier)
            g.all_units.append(su)
            g.player_units.append(su)
            g.map.get_cell(spawn_x, spawn_y).units.append(su)
            if target_unit and target_unit.is_alive:
                g.set_waypoint_destination(su, target_unit.x, target_unit.y)
                g.message = f"{soldier.full_name} вышел и идёт к {target_unit.name}"
            else:
                g.message = f"{soldier.full_name} выведен из отряда как отдельный юнит"
            g.selected_soldier_idx = None
            g.soldier_transfer_mode = False
            g.soldier_detail_idx = None
            if not g.soldier_source_unit.alive_soldiers:
                g.exit_soldier_management()
            return True
        g.message = "Не удалось вывести солдата"
        return False

    def load_soldier_to_truck(self, soldier, truck):
        g = self.game
        if not isinstance(truck, SupplyTruck) or not truck.is_alive:
            g.message = "Это не грузовик"
            return False
        if not hasattr(g.soldier_source_unit, 'soldiers_list'):
            g.message = "Исходный юнит не имеет личного состава"
            return False
        src = g.map.get_cell(g.soldier_source_unit.x, g.soldier_source_unit.y)
        dst = g.map.get_cell(truck.x, truck.y)
        if src != dst:
            g.message = "Грузовик должен быть на той же клетке"
            return False
        if len(truck.alive_soldiers) >= truck.max_soldiers:
            g.message = "В грузовике нет мест"
            return False
        if g.soldier_source_unit.transfer_soldier(soldier, truck):
            g.message = f"{soldier.full_name} погружен в {truck.name}"
            return True
        g.message = "Не удалось погрузить"
        return False

    def send_soldier_to_reserve(self, soldier):
        g = self.game
        src = g.soldier_source_unit
        if not src or not hasattr(src, 'soldiers_list'):
            return False
        cell = g.map.get_cell(src.x, src.y)
        warehouse = None
        if cell:
            for u in cell.units:
                if isinstance(u, Warehouse) and u.faction == config.PLAYER and u.is_alive:
                    warehouse = u
                    break
        if not warehouse:
            g.message = "Нужно быть на складе для отправки в резерв"
            return False
        if src.remove_soldier(soldier):
            warehouse.add_to_reserve(soldier)
            g.message = f"{soldier.full_name} отправлен в резерв на складе {warehouse.name}"
            if not src.alive_soldiers:
                g.exit_soldier_management()
            return True
        return False

    def order_exit_garrison(self):
        g = self.game
        cache = g.selected_unit
        if not cache or not isinstance(cache, SupplyCache) or not cache.is_alive:
            g.message = "Выберите погреб"
            return
        if cache.build_turns < cache.build_required:
            g.message = "Погреб ещё строится"
            return
        if cache.garrison <= 0:
            g.message = "Нет гарнизона"
            return
        for nx, ny in g.map.get_neighbors(cache.x, cache.y):
            cell = g.map.get_cell(nx, ny)
            if not cell or not cell.is_walkable:
                continue
            if any(u.x == nx and u.y == ny and u.is_alive for u in g.all_units):
                continue
            inf = Infantry(nx, ny, config.PLAYER, f"Отряд {cache.name.split()[-1]}", soldiers=config.GARRISON_EXIT_SOLDIERS)
            g.map.add_unit(inf, nx, ny)
            g.all_units.append(inf)
            g.player_units.append(inf)
            cache.garrison -= 1
            g.message = f"Отряд вышел из {cache.name}"
            return
        g.message = "Нет места для выхода"

    # ── attack commands ───────────────────────────────────────────────

    def order_attack(self, target):
        g = self.game
        attacker = g.selected_unit
        if not attacker or not attacker.is_alive or attacker.attacked:
            g.message = "Не может атаковать"
            return None
        if getattr(attacker, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для атаки"
            return None
        if hasattr(attacker, 'jammed') and attacker.jammed:
            g.message = "Нет связи! Дрон неуправляем"
            return None
        if not target or not target.is_alive:
            return None
        current_faction = g.current_player_faction if g.game_mode == "hotseat" else config.PLAYER
        if attacker.faction != current_faction:
            g.message = "Этот юнит не ваш"
            return None
        enemy_faction = config.ENEMY if current_faction == config.PLAYER else config.PLAYER
        if target.faction != enemy_faction:
            return None
        dist = g.map.distance(attacker.x, attacker.y, target.x, target.y)
        atk_range = config.INFANTRY_ATTACK_RANGE
        if isinstance(attacker, Tank):
            atk_range = config.TANK_ATTACK_RANGE
        if dist > atk_range:
            g.message = "Цель вне зоны досягаемости"
            return None
        result = resolve_attack(attacker, target)
        if result:
            attacker.attacked = True
            g.combat_log.append(result)
            g.message = result["message"]
            if not result["defender_alive"]:
                target.die()
                g.map.remove_unit(target)
                for lst in (g.all_units, g.enemy_units):
                    if target in lst:
                        lst.remove(target)
                if target not in g.dead_units:
                    g.dead_units.append(target)
            if not result["attacker_alive"]:
                attacker.die()
                g.map.remove_unit(attacker)
                if attacker not in g.dead_units:
                    g.dead_units.append(attacker)
                g.message += " | Атакующий уничтожен!"
        g.selected_unit = None
        return result

    def order_attack_cell(self, gx, gy):
        g = self.game
        unit = g.selected_unit
        if not unit or not isinstance(unit, Tank) or not unit.is_alive:
            g.message = "Только танк может атаковать клетку"
            return
        if getattr(unit, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для атаки"
            return
        if unit.attacked:
            g.message = "Уже атаковал"
            return
        if unit.ammo <= 0:
            g.message = "Нет боезапаса"
            return
        dist = abs(unit.x - gx) + abs(unit.y - gy)
        if dist > config.TANK_CELL_ATTACK_RANGE:
            g.message = f"Слишком далеко (макс {config.TANK_CELL_ATTACK_RANGE} клетки)"
            return
        cell = g.map.get_cell(gx, gy)
        if not cell:
            return
        unit.ammo -= 1
        unit.attacked = True
        hit = False
        for target in list(cell.units):
            if target.faction == config.ENEMY and target.is_alive:
                if isinstance(target, Infantry):
                    dmg = random.randint(1, unit.attack_power + config.TANK_VS_INF_MELEE_BONUS)
                    alive = target.alive_soldiers
                    to_kill = min(len(alive), dmg)
                    for s in random.sample(alive, to_kill):
                        s.is_alive = False
                    if target.soldiers <= 0:
                        target.die()
                elif isinstance(target, Tank):
                    dmg = random.randint(1, unit.attack_power)
                    target.take_damage(dmg)
                else:
                    target.die()
                hit = True
                g.message = f"{unit.name} обстрелял ({gx},{gy})! {target.name} ранен"
                if not target.is_alive:
                    g.map.remove_unit(target)
                    for lst in (g.all_units, g.enemy_units):
                        if target in lst:
                            lst.remove(target)
                    if target not in g.dead_units:
                        g.dead_units.append(target)
                    g.message += " (уничтожен)"
        if not hit:
            g.message = f"{unit.name} обстрелял ({gx},{gy}) — нет целей"
        g.selected_unit = None
        return hit

    def order_fpv_strike(self, target):
        g = self.game
        if not g.selected_unit or not isinstance(g.selected_unit, ReconDrone):
            g.message = "Выберите дрон-разведчик"
            return None
        if getattr(g.selected_unit, 'is_understaffed', False):
            g.message = "Недостаточно экипажа для FPV-удара"
            return None
        drone = g.selected_unit
        dist = g.map.distance(drone.x, drone.y, target.x, target.y)
        if dist > drone.vision_range:
            g.message = "Цель вне зоны видимости дрона"
            return None
        warehouse = None
        for u in g.player_units:
            if isinstance(u, Warehouse) and u.faction == config.PLAYER and u.fpv_drones > 0:
                warehouse = u
                break
        if not warehouse:
            g.message = "Нет FPV-дронов на складе"
            return None
        result = resolve_fpv_strike(drone, target, warehouse, g.map)
        if result:
            g.combat_log.append(result)
            g.message = result["message"]
            if not result.get("hit", False):
                return result
            if not target.is_alive:
                g.map.remove_unit(target)
                for lst in (g.all_units, g.enemy_units):
                    if target in lst:
                        lst.remove(target)
                if target not in g.dead_units:
                    g.dead_units.append(target)
        g.selected_unit = None
        return result

    # ── warehouse move ───────────────────────────────────────────────

    def start_move_warehouse(self):
        g = self.game
        g.moving_warehouse = True
        g.message = "Кликните на новое место для склада"

    def confirm_move_warehouse(self, tx, ty):
        g = self.game
        g.moving_warehouse = False
        cell = g.map.get_cell(tx, ty)
        if not cell or not cell.is_walkable:
            g.message = "Нельзя переместить склад сюда"
            return
        wh = next((u for u in g.player_units if isinstance(u, Warehouse) and u.is_alive), None)
        if not wh:
            g.message = "Нет склада"
            return
        dist = abs(wh.x - tx) + abs(wh.y - ty)
        if dist > config.WAREHOUSE_MOVE_MAX_DISTANCE:
            g.message = f"Слишком далеко (макс {config.WAREHOUSE_MOVE_MAX_DISTANCE} клетки)"
            return
        g.map.remove_unit(wh)
        wh.x, wh.y = tx, ty
        g.map.add_unit(wh, tx, ty)
        g.message = f"Склад перемещён на ({tx},{ty})"
