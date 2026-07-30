import pygame
from . import config
from .units import Infantry, Tank, ReconDrone, FPVDrone, SupplyTruck, Warehouse, Artillery, FPVOperator, ReconOperator, RadarEW
from .utils.save_load import SaveLoadSystem
from .ui.esp_menu import ESPMenu


class UIManager:
    def __init__(self, game):
        self.game = game
        self.keys = {}
        self.mouse_pos = (0, 0)
        self.selected_for_attack = False
        self.shift_held = False
        self.cheat_console_open = False
        self.cheat_input = ""
        self.esp_menu = ESPMenu()

    def handle_event(self, event, renderer):
        self.mouse_pos = pygame.mouse.get_pos()

        # ESP menu handling - приоритет выше
        if self.esp_menu.is_open:
            self.esp_menu.handle_event(event)
            if self.esp_menu.is_open:
                return

        if event.type == pygame.KEYDOWN:
            self.keys[event.key] = True
            self._handle_key(event.key, renderer)
        elif event.type == pygame.KEYUP:
            self.keys[event.key] = False
            if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                self.shift_held = False
                self.selected_for_attack = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse(event, renderer)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                renderer.dragging = False
                renderer.drag_start = None

        elif event.type == pygame.MOUSEMOTION:
            self._handle_motion(event, renderer)

    def _handle_key(self, key, renderer):
        if self.game.game_over:
            return

        # Cheat console handling
        if self.cheat_console_open:
            self._handle_cheat_console_key(key)
            return

        # ESP menu - Tab key
        if key == pygame.K_TAB:
            self.esp_menu.toggle()
            if self.esp_menu.is_open:
                self.game.message = "ESP меню открыто (Tab/Esc - закрыть)"
            else:
                self.game.message = ""
            return

        # Hot-seat mode: waiting for player switch confirmation
        if self.game.waiting_for_hotseat_switch:
            if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
                self.game.confirm_hotseat_switch()
            return

        # Shift+P - Save game
        if key == pygame.K_p and self.shift_held:
            slot_name = f"save_turn_{self.game.turn}"
            SaveLoadSystem.save_game(self.game, slot_name)
            self.game.message = f"Игра сохранена: {slot_name}"
            return

        # Shift+C - Open cheat console
        if key == pygame.K_c and self.shift_held:
            self.cheat_console_open = True
            self.cheat_input = ""
            self.game.message = "Консоль читов открыта (ESC - закрыть)"
            return

        if key == pygame.K_s:
            unit = self.game.selected_unit
            if hasattr(unit, 'soldiers_list') and unit.is_alive:
                if self.game.soldier_management_mode:
                    self.game.exit_soldier_management()
                else:
                    self.game.enter_soldier_management(unit)
            return

        if key == pygame.K_e:
            self.game.order_entrench()

        elif key == pygame.K_c:
            self.game.order_build_cache()

        elif key == pygame.K_t:
            self.game.order_start_supply_line()

        elif key == pygame.K_x:
            self.game.order_cancel_supply_line()

        elif key == pygame.K_l:
            self.game.load_truck()

        elif key == pygame.K_u:
            self.game.unload_truck()

        elif key == pygame.K_b:
            self.game.load_operator_batteries()
        elif key == pygame.K_f:
            self.game.order_unload_ammo()
        elif key == pygame.K_n:
            # Прямая передача грузов между юнитами
            self.game.order_transfer_cargo()
        elif key == pygame.K_j:
            # Присоединить одиночного бойца к отряду
            self.game.order_join_squad()
        elif key == pygame.K_o:
            # Организовать отделение из двух одиночных бойцов
            self.game.order_form_squad()
        elif key == pygame.K_i:
            # Загрузить одиночного бойца в грузовик
            self.game.order_load_single_to_truck()
        elif key == pygame.K_g:
            self.game.order_exit_garrison()
        elif key == pygame.K_v:
            unit = self.game.selected_unit
            if isinstance(unit, SupplyTruck) and unit.is_alive:
                if unit.auto_mix:
                    unit.auto_mix = False
                    unit.load_choice = 0
                    self.game.message = f"Груз: {config.CARGO_NAMES.get(unit.current_load_type, unit.current_load_type)}"
                else:
                    nxt = (unit.load_choice + 1) % len(SupplyTruck.CARGO_CYCLE)
                    unit.load_choice = nxt
                    if nxt == 0:
                        unit.auto_mix = True
                        self.game.message = "Грузовик: везём всё подряд"
                    else:
                        self.game.message = f"Груз: {config.CARGO_NAMES.get(unit.current_load_type, unit.current_load_type)}"
        elif key == pygame.K_m:
            self.game.start_move_warehouse()
        elif key == pygame.K_r:
            self.game.radar_mode = not self.game.radar_mode
            self.game.message = f"Радар: {'вкл' if self.game.radar_mode else 'выкл'}"
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            idx = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4].index(key)
            ct = SupplyTruck.CARGO_CYCLE[idx]
            sel = self.game.selected_unit
            if sel and isinstance(sel, Warehouse):
                self.game.load_truck(load_type=ct)
            elif sel and isinstance(sel, SupplyTruck) and sel.is_alive:
                sel.auto_mix = False
                sel.load_choice = idx
                self.game.message = f"Груз: {config.CARGO_NAMES.get(ct, ct)}"
            elif self.game.selected_unit and isinstance(self.game.selected_unit, SupplyTruck):
                self.game.unload_truck()

        elif key == pygame.K_LSHIFT or key == pygame.K_RSHIFT:
            self.shift_held = True

        elif key == pygame.K_ESCAPE:
            if self.game.soldier_management_mode:
                self.game.exit_soldier_management()
                return
            if self.game.cargo_transfer_mode:
                self.cancel_cargo_transfer()
                self.game.message = "Передача груза отменена"
                return
            if self.game.transfer_mode:
                self.game.cancel_transfer_mode()
                self.game.message = "Передача отменена"
                return
            self.game.selected_unit = None
            self.game.pinned_cell = None
            self.game.origin_select_mode = None
            self.game.dest_select_mode = None
            self.game.supply_line_select_mode = None
            self.game.deliver_target_mode = None
            self.game.artillery_barrage_mode = None
            self.game.join_move_mode = False

        # Camera movement
        elif key == pygame.K_LEFT:
            renderer.handle_scroll(config.CAMERA_SCROLL_SPEED, 0)
        elif key == pygame.K_RIGHT:
            renderer.handle_scroll(-config.CAMERA_SCROLL_SPEED, 0)
        elif key == pygame.K_UP:
            renderer.handle_scroll(0, config.CAMERA_SCROLL_SPEED)
        elif key == pygame.K_DOWN:
            renderer.handle_scroll(0, -config.CAMERA_SCROLL_SPEED)
        elif key == pygame.K_PLUS or key == pygame.K_KP_PLUS or key == pygame.K_EQUALS:
            renderer.zoom_in(anchor=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))
        elif key == pygame.K_MINUS or key == pygame.K_KP_MINUS:
            renderer.zoom_out(anchor=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2))

    def _handle_mouse(self, event, renderer):
        mx, my = event.pos
        
        # Check for panel area clicks
        if mx >= config.SCREEN_WIDTH - config.PANEL_WIDTH:
            if event.button == 1:
                # Check hourglass button FIRST - always accessible
                if hasattr(renderer, 'hourglass_rect') and renderer.hourglass_rect.collidepoint(mx, my):
                    if self.game.phase == config.PHASE_PLANNING:
                        self.game.end_planning_phase()
                    return

                # Check soldier detail view buttons
                if self.game.soldier_management_mode and self.game.soldier_detail_idx is not None and hasattr(renderer, 'soldier_detail_rects'):
                    for action, rect in renderer.soldier_detail_rects:
                        if rect.collidepoint(mx, my):
                            if action == "back":
                                self.game.soldier_detail_idx = None
                                self.game.selected_soldier_idx = None
                                self.game.soldier_transfer_mode = False
                                self.game.message = "Кликните на солдата для просмотра"
                                return
                            elif action == "transfer":
                                unit = self.game.soldier_source_unit
                                soldiers = unit.alive_soldiers
                                if self.game.selected_soldier_idx is not None and self.game.selected_soldier_idx < len(soldiers):
                                    self.game.confirm_transfer_soldier(None)
                                return
                            elif action == "load_truck":
                                unit = self.game.soldier_source_unit
                                soldiers = unit.alive_soldiers
                                if self.game.selected_soldier_idx is not None and self.game.selected_soldier_idx < len(soldiers):
                                    soldier = soldiers[self.game.selected_soldier_idx]
                                    src_cell = self.game.map.get_cell(unit.x, unit.y)
                                    if src_cell:
                                        for u in src_cell.units:
                                            if isinstance(u, SupplyTruck) and u.is_alive and u.faction == unit.faction:
                                                if self.game.load_soldier_to_truck(soldier, u):
                                                    self.game.soldier_detail_idx = None
                                                    self.game.selected_soldier_idx = None
                                                break
                                return
                            elif action == "send_reserve":
                                unit = self.game.soldier_source_unit
                                soldiers = unit.alive_soldiers
                                if self.game.selected_soldier_idx is not None and self.game.selected_soldier_idx < len(soldiers):
                                    soldier = soldiers[self.game.selected_soldier_idx]
                                    self.game.send_soldier_to_reserve(soldier)
                                    self.game.soldier_detail_idx = None
                                    self.game.selected_soldier_idx = None
                                return
                            elif action == "transfer_to_unit":
                                self.game.soldier_detail_idx = None
                                self.game.select_soldier_for_transfer(self.game.selected_soldier_idx)
                                return
                    return

                # Check soldier list click (in soldier management mode)
                if self.game.soldier_management_mode and hasattr(renderer, 'soldier_rects'):
                    for idx, rect in renderer.soldier_rects:
                        if rect.collidepoint(mx, my):
                            self.game.soldier_detail_idx = idx
                            self.game.selected_soldier_idx = idx
                            self.game.message = "Просмотр солдата. Кнопка 'Перевести' для перевода"
                            return
                
                # Check action buttons
                if hasattr(renderer, 'action_buttons_rects'):
                    for btn_rect, action in renderer.action_buttons_rects:
                        if btn_rect.collidepoint(mx, my):
                            self._handle_button_click(action)
                            return
            return

        if event.button == 2:  # Middle click - start drag
            renderer.dragging = True
            renderer.drag_start = (mx, my)
            return

        if event.button == 3 and renderer.dragging:  # Right click - end drag alternative
            renderer.dragging = False
            renderer.drag_start = None
            return

        gx, gy = renderer.screen_to_map(mx, my)
        cell = self.game.map.get_cell(gx, gy)
        if not cell:
            return

        if event.button == 1:  # Left click
            if renderer.dragging:
                return
            if self.game.phase != config.PHASE_PLANNING:
                return

            current_faction = self.game.current_player_faction if self.game.game_mode == "hotseat" else config.PLAYER

            # If supply line select mode, assign destination
            if self.game.supply_line_select_mode:
                self.game.order_assign_supply_dest(gx, gy)
                return

            # If origin select mode, assign warehouse
            if self.game.origin_select_mode:
                self.game.confirm_set_origin(gx, gy)
                return

            # If dest select mode, assign cache
            if self.game.dest_select_mode:
                self.game.confirm_set_dest(gx, gy)
                return

            # If deliver target mode, assign delivery target
            if self.game.deliver_target_mode:
                self.game.confirm_deliver_to_unit(gx, gy)
                return

            # If artillery barrage mode, fire at target
            if self.game.artillery_barrage_mode:
                self.game.confirm_artillery_barrage(gx, gy)
                return

            # If cargo transfer mode, transfer cargo to clicked unit
            if self.game.cargo_transfer_mode:
                self.confirm_cargo_transfer(gx, gy)
                return

            # If soldier transfer mode, try to transfer to target unit
            if self.game.soldier_transfer_mode:
                target_unit = None
                for u in cell.units:
                    if u.faction == current_faction and u.is_alive and hasattr(u, 'soldiers_list'):
                        target_unit = u
                        break
                if target_unit:
                    self.game.confirm_transfer_soldier(target_unit)
                else:
                    self.game.message = "Выберите юнит для перевода"
                return

            # If resource transfer mode, try to transfer to target unit
            if self.game.transfer_mode:
                target_unit = None
                for u in cell.units:
                    if u.faction == current_faction and u.is_alive and u is not self.game.transfer_source:
                        target_unit = u
                        break
                if target_unit:
                    self.game.confirm_transfer_to_target(target_unit)
                else:
                    self.game.message = "Выберите юнит для передачи (ESC - отмена)"
                return

            # If moving warehouse mode, confirm move
            if self.game.moving_warehouse:
                self.game.confirm_move_warehouse(gx, gy)
                return

            # If join move mode, select target
            if self.game.join_move_mode:
                target_unit = None
                for u in cell.units:
                    if u.is_alive and isinstance(u, Infantry) and u.faction == current_faction:
                        target_unit = u
                        break
                if target_unit:
                    self.game._action_mgr.execute_join_squad_move(target_unit)
                else:
                    self.game.message = "Кликните на свой отряд (ESC - отмена)"
                return

            unit_at = None
            if cell.units:
                # Find first unit of current faction
                for u in cell.units:
                    if u.faction == current_faction and u.is_alive:
                        unit_at = u
                        break

            if unit_at:
                self.game.select_unit(unit_at)
                self.game.pinned_cell = None
            elif self.game.selected_unit and self.game.selected_unit.is_alive:
                if self.shift_held:
                    self._handle_attack_click(gx, gy)
                else:
                    self.game.move_selected_unit(gx, gy)

        elif event.button == 3:  # Right click
            if self.shift_held or self.selected_for_attack:
                return
            unit = self.game.selected_unit
            # Tank area attack on right-click cell within 2 cells
            if isinstance(unit, Tank) and unit.is_alive and not unit.attacked and unit.ammo > 0:
                dist = abs(unit.x - gx) + abs(unit.y - gy)
                if dist <= 2:
                    self.game.order_attack_cell(gx, gy)
                    return
            # Pin cell: show info, center camera
            self.game.pinned_cell = (gx, gy)
            # Center camera on this cell
            ts = renderer.tsize
            view_w = config.SCREEN_WIDTH - config.PANEL_WIDTH
            view_h = config.SCREEN_HEIGHT
            renderer.camera_x = -(gx * ts - view_w // 2 + ts // 2)
            renderer.camera_y = -(gy * ts - view_h // 2 + ts // 2)
            renderer._clamp_camera()
            # Show cell info in message
            terr_name = cell.name
            self.game.message = f"Клетка ({gx}, {gy}): {terr_name}, юнитов: {len(cell.units)}"

        elif event.button == 4:  # Wheel up - zoom in at cursor
            renderer.zoom_in(anchor=(mx, my))
        elif event.button == 5:  # Wheel down - zoom out at cursor
            renderer.zoom_out(anchor=(mx, my))

    def _handle_button_click(self, action):
        """Обработка нажатия кнопки действия"""
        if not action:
            return
        
        unit = self.game.selected_unit
        if not unit or not unit.is_alive:
            return
        
        # Обработка кликов по кнопкам ресурсов
        if action.startswith("resource_"):
            res_type = action[9:]  # Убираем "resource_"
            self._handle_resource_click(unit, res_type)
            return
        
        # Обработка кликов по кнопкам груза грузовика
        if action.startswith("cargo_"):
            cargo_type = action[6:]  # Убираем "cargo_"
            self._handle_cargo_click(unit, cargo_type)
            return
        
        if action == "soldier_management":
            if self.game.soldier_management_mode:
                self.game.exit_soldier_management()
            else:
                self.game.enter_soldier_management(unit)
            return
        
        if action == "toggle_ew":
            if isinstance(unit, RadarEW):
                unit.toggle()
                status = "включен" if unit.active else "выключен"
                self.game.message = f"РЭБ {status}"
            return
        
        if action == "deploy_drone":
            if isinstance(unit, ReconOperator):
                drone, msg = unit.deploy_drone(self.game)
                self.game.message = msg
            return
        
        if action == "load_recon_drone":
            if isinstance(unit, SupplyTruck):
                cell = self.game.map.get_cell(unit.x, unit.y)
                if cell:
                    for u in cell.units:
                        if u.is_alive and u.faction == unit.faction and isinstance(u, (Warehouse, SupplyCache)):
                            if isinstance(u, SupplyCache) and u.build_turns < u.build_required:
                                continue
                            if unit.load_recon_drone_from_warehouse(u):
                                self.game.message = "Разведдрон загружен в грузовик"
                            else:
                                self.game.message = "Невозможно загрузить дрон"
                            break
            return
        
        if action == "deliver_recon_drone":
            if isinstance(unit, SupplyTruck):
                for u in self.game.all_units:
                    if isinstance(u, ReconOperator) and u.is_alive and u.faction == unit.faction and \
                       abs(u.x - unit.x) + abs(u.y - unit.y) <= 1 and u.drone_stored < u.max_drone_stored:
                        if unit.unload_recon_drone_to_operator(u):
                            self.game.message = f"Дрон доставлен → {u.name}"
                        else:
                            self.game.message = "Невозможно передать дрон"
                        break
            return
        
        if action == "load_fpv_drone":
            if isinstance(unit, SupplyTruck):
                cell = self.game.map.get_cell(unit.x, unit.y)
                if cell:
                    for u in cell.units:
                        if u.is_alive and u.faction == unit.faction and isinstance(u, (Warehouse, SupplyCache)):
                            if isinstance(u, SupplyCache) and u.build_turns < u.build_required:
                                continue
                            if unit.load_fpv_drone_from_warehouse(u):
                                self.game.message = "FPV-дроны загружены в грузовик"
                            else:
                                self.game.message = "Невозможно загрузить FPV-дроны"
                            break
            return
        
        if action == "deliver_fpv_drone":
            if isinstance(unit, SupplyTruck):
                for u in self.game.all_units:
                    if isinstance(u, FPVOperator) and u.is_alive and u.faction == unit.faction and \
                       abs(u.x - unit.x) + abs(u.y - unit.y) <= 1 and u.fpv_stock < u.max_stock:
                        if unit.unload_fpv_drone_to_operator(u):
                            self.game.message = f"FPV-дроны доставлены → {u.name}"
                        else:
                            self.game.message = "Невозможно передать FPV-дроны"
                        break
            return
        
        if self.game.phase != config.PHASE_PLANNING:
            return
        
        if action == "entrench":
            self.game.order_entrench()
        elif action == "build_cache":
            self.game.order_build_cache()
        elif action == "unload_ammo":
            self.game.order_unload_ammo()
        elif action == "toggle_fpv":
            if hasattr(unit, 'auto_mode'):
                unit.auto_mode = not unit.auto_mode
                mode = "авто" if unit.auto_mode else "ручной"
                self.game.message = f"Режим FPV: {mode}"
        elif action == "artillery_barrage":
            self.game.order_artillery_barrage()
        elif action == "load_batteries":
            self.game.load_operator_batteries()
        elif action == "toggle_mix":
            if isinstance(unit, SupplyTruck):
                if unit.auto_mix:
                    unit.auto_mix = False
                    unit.load_choice = 0
                    ct = unit.current_load_type
                    self.game.message = f"Груз: {config.CARGO_NAMES.get(ct, ct)}"
                else:
                    nxt = (unit.load_choice + 1) % len(SupplyTruck.CARGO_CYCLE)
                    unit.load_choice = nxt
                    if nxt == 0:
                        unit.auto_mix = True
                        self.game.message = "Грузовик: везём всё подряд"
                    else:
                        ct = unit.current_load_type
                        self.game.message = f"Груз: {config.CARGO_NAMES.get(ct, ct)}"
        elif action == "load":
            self.game.load_truck()
        elif action == "unload":
            self.game.unload_truck()
        elif action == "cancel_route":
            self.game.order_cancel_supply_line()
        elif action == "start_route":
            self.game._try_start_route(unit)
        elif action == "set_origin":
            self.game.order_set_origin()
        elif action == "set_dest":
            self.game.order_set_dest()
        elif action == "deliver_to_unit":
            self.game.order_deliver_to_unit()
        elif action == "wh_transfer_to_unit":
            self.game.warehouse_transfer_to_unit()
        elif action.startswith("wh_transfer_"):
            # Передача ресурсов из склада в конкретный юнит
            idx_str = action.split("_")[-1]
            try:
                target_idx = int(idx_str)
                target = self.game.all_units[target_idx]
                self.game.warehouse_transfer_to_unit_direct(target)
            except (ValueError, IndexError):
                self.game.message = "Ошибка передачи"
        elif action == "move_warehouse":
            self.game.start_move_warehouse()
        elif action == "exit_garrison":
            self.game.order_exit_garrison()
        elif action == "join_squad":
            self.game.order_join_squad()
        elif action == "join_squad_move":
            self.game.order_join_squad_move()
        elif action == "form_squad":
            self.game.order_form_squad()
        elif action == "load_to_truck":
            self.game.order_load_single_to_truck()
        elif action.startswith("cache_transfer_"):
            # Передача ресурсов из погреба в юнит
            idx_str = action.split("_")[-1]
            try:
                target_idx = int(idx_str)
                target = self.game.all_units[target_idx]
                self.game.transfer_from_cache_to_unit(unit, target)
            except (ValueError, IndexError):
                self.game.message = "Ошибка передачи"
        elif action.startswith("wh_transfer_"):
            # Передача ресурсов из склада в юнит
            idx_str = action.split("_")[-1]
            try:
                target_idx = int(idx_str)
                target = self.game.all_units[target_idx]
                self.game.warehouse_transfer_to_unit_direct(target)
            except (ValueError, IndexError):
                self.game.message = "Ошибка передачи"
        elif action.startswith("load_"):
            cargo_type = action[5:]
            if cargo_type == "supplies":
                self.game.load_truck(load_type=config.CARGO_SUPPLIES)
            elif cargo_type == "ammo":
                self.game.load_truck(load_type=config.CARGO_AMMO)
            elif cargo_type == "fuel":
                self.game.load_truck(load_type=config.CARGO_FUEL)
            elif cargo_type == "batteries":
                self.game.load_truck(load_type=config.CARGO_BATTERIES)

    def _handle_resource_click(self, unit, res_type):
        """Обработка клика по кнопке ресурса - начало режима передачи"""
        self.game.start_transfer_mode(res_type)

    def _handle_cargo_click(self, truck, cargo_type):
        """Обработка клика по кнопке груза - начало выбора цели"""
        if not isinstance(truck, SupplyTruck) or not truck.is_alive:
            self.game.message = "Выберите грузовик"
            return
        
        available = truck.cargo.get(cargo_type, 0)
        if available <= 0:
            self.game.message = f"Нет груза: {config.CARGO_NAMES.get(cargo_type, cargo_type)}"
            return
        
        # Входим в режим передачи груза
        self.game.cargo_transfer_mode = True
        self.game.cargo_transfer_truck = truck
        self.game.cargo_transfer_type = cargo_type
        self.game.message = f"Кликните на юнита для передачи {config.CARGO_NAMES.get(cargo_type, cargo_type)}"

    def confirm_cargo_transfer(self, gx, gy):
        """Подтвердить передачу груза по клику на карту"""
        truck = self.game.cargo_transfer_truck
        cargo_type = self.game.cargo_transfer_type
        
        if not truck or not truck.is_alive:
            self.cancel_cargo_transfer()
            return
        
        # Ищем юнита в клетке
        cell = self.game.map.get_cell(gx, gy)
        if not cell:
            self.game.message = "Нет клетки"
            return
        
        target = None
        for u in cell.units:
            if u is not truck and u.is_alive and u.faction == truck.faction:
                if not isinstance(u, (ReconDrone, FPVDrone)):
                    target = u
                    break
        
        if not target:
            self.game.message = "Нет союзника в этой клетке"
            return
        
        # Выполняем передачу
        amount = truck.unload(cargo_type, 5)
        if amount > 0:
            self._apply_cargo_to_unit(target, cargo_type, amount)
            
            # Подсветка
            self.game.cargo_transfer_source = truck
            self.game.cargo_transfer_target = target
            self.game.cargo_transfer_timer = 20
            
            # Анимация
            self.game._add_resource_transfer_effect(truck, target)
            self.game.message = f"Передано {amount} {config.CARGO_NAMES.get(cargo_type, cargo_type)} → {target.name}"
        else:
            self.game.message = "Ошибка передачи"
        
        # Выходим из режима
        self.cancel_cargo_transfer()

    def cancel_cargo_transfer(self):
        """Отменить режим передачи груза"""
        self.game.cargo_transfer_mode = False
        self.game.cargo_transfer_truck = None
        self.game.cargo_transfer_type = None

    def _apply_cargo_to_unit(self, unit, cargo_type, amount):
        """Применить груз к юниту"""
        if isinstance(unit, Infantry):
            for s in unit.alive_soldiers:
                if amount <= 0:
                    break
                if cargo_type == config.CARGO_SUPPLIES:
                    give = min(amount, s.max_food - s.food)
                    s.food += give
                    amount -= give
                elif cargo_type == config.CARGO_AMMO:
                    give = min(amount, s.max_ammo - s.ammo)
                    s.ammo += give
                    amount -= give
        elif isinstance(unit, Tank):
            if cargo_type == config.CARGO_AMMO:
                give = min(amount, unit.max_ammo - unit.ammo)
                unit.ammo += give
            elif cargo_type == config.CARGO_FUEL:
                give = min(amount, unit.max_fuel - unit.fuel)
                unit.fuel += give
            elif cargo_type == config.CARGO_SUPPLIES:
                give = min(amount, unit.max_carry_food - unit.carry_food)
                unit.carry_food += give
        elif isinstance(unit, Artillery):
            if cargo_type == config.CARGO_AMMO:
                give = min(amount, unit.max_ammo - unit.ammo)
                unit.ammo += give
            elif cargo_type == config.CARGO_SUPPLIES:
                for s in unit.alive_soldiers:
                    if amount <= 0:
                        break
                    give = min(amount, s.max_food - s.food)
                    s.food += give
                    amount -= give
        elif isinstance(unit, ReconOperator):
            if cargo_type == config.CARGO_BATTERIES:
                give = min(amount, unit.max_batteries - unit.batteries)
                unit.batteries += give
            elif cargo_type == config.CARGO_SUPPLIES:
                give = min(amount, unit.max_food - unit.food)
                unit.food += give
            elif cargo_type == config.CARGO_AMMO:
                give = min(amount, unit.max_ammo - unit.ammo)
                unit.ammo += give
        elif isinstance(unit, FPVOperator):
            if cargo_type == config.CARGO_SUPPLIES:
                give = min(amount, unit.max_food - unit.food)
                unit.food += give
            elif cargo_type == config.CARGO_AMMO:
                give = min(amount, unit.max_ammo - unit.ammo)
                unit.ammo += give
        elif isinstance(unit, SupplyTruck):
            unit.cargo[cargo_type] = unit.cargo.get(cargo_type, 0) + amount

    def _handle_attack_click(self, gx, gy):
        cell = self.game.map.get_cell(gx, gy)
        if not cell:
            return
        
        # Если выбрана артиллерия, атакуем клетку
        if isinstance(self.game.selected_unit, Artillery):
            self.game.order_artillery_attack(gx, gy)
            return
        
        # Determine enemy faction based on current player
        current_faction = self.game.current_player_faction if self.game.game_mode == "hotseat" else config.PLAYER
        enemy_faction = config.ENEMY if current_faction == config.PLAYER else config.PLAYER
        
        for u in cell.units:
            if u.faction == enemy_faction and u.is_alive:
                self.game.order_attack(u)
                break

    def _handle_motion(self, event, renderer):
        mx, my = event.pos

        # Mouse drag camera panning
        if renderer.dragging and renderer.drag_start:
            dx = mx - renderer.drag_start[0]
            dy = my - renderer.drag_start[1]
            renderer.camera_x += dx
            renderer.camera_y += dy
            renderer._clamp_camera()
            renderer.drag_start = (mx, my)
            return

        if mx >= config.SCREEN_WIDTH - config.PANEL_WIDTH:
            self.game.hovered_cell = None
            return

        gx, gy = renderer.screen_to_map(mx, my)
        cell = self.game.map.get_cell(gx, gy)
        if cell:
            self.game.hovered_cell = (gx, gy)
        else:
            self.game.hovered_cell = None

        # Screen edge scrolling
        w, h = config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT
        if mx < 10:
            renderer.handle_scroll(config.EDGE_SCROLL_SPEED, 0)
        elif mx > w - 10:
            renderer.handle_scroll(-config.EDGE_SCROLL_SPEED, 0)
        if my < 10:
            renderer.handle_scroll(0, config.EDGE_SCROLL_SPEED)
        elif my > h - 10:
            renderer.handle_scroll(0, -config.EDGE_SCROLL_SPEED)

    def _handle_cheat_console_key(self, key):
        """Обработка клавиш в консоли читов"""
        if key == pygame.K_ESCAPE:
            self.cheat_console_open = False
            self.cheat_input = ""
            self.game.message = "Консоль читов закрыта"
            return
        
        if key == pygame.K_RETURN:
            self._execute_cheat(self.cheat_input)
            self.cheat_input = ""
            self.cheat_console_open = False
            return
        
        if key == pygame.K_BACKSPACE:
            self.cheat_input = self.cheat_input[:-1]
            return
        
        # Добавляем символы
        if key == pygame.K_SPACE:
            self.cheat_input += " "
        elif pygame.K_a <= key <= pygame.K_z:
            char = chr(key)
            if self.shift_held:
                char = char.upper()
            else:
                char = char.lower()
            self.cheat_input += char
        elif pygame.K_0 <= key <= pygame.K_9 and not self.shift_held:
            self.cheat_input += chr(key)

    def _execute_cheat(self, cheat_code):
        """Выполнить чит-код"""
        code = cheat_code.strip().lower()
        
        if code == "fog":
            # Убрать туман войны для текущей фракции
            self.game.fog_disabled = True
            self.game.reveal_all_enemies = True
            current_faction = self.game.current_player_faction if self.game.game_mode == "hotseat" else config.PLAYER
            for y in range(self.game.map.height):
                for x in range(self.game.map.width):
                    cell = self.game.map.get_cell(x, y)
                    if cell:
                        cell.visible = True
                        cell.explored = True
                        if current_faction == config.PLAYER:
                            cell.explored_player = True
                        else:
                            cell.explored_enemy = True
            self.game.message = "Туман войны убран (навсегда)"
        
        elif code == "reveal":
            # Показать всех вражеских юнитов (временно)
            self.game.reveal_all_enemies = True
            self.game.message = "Все враги видны (до следующего хода)"
        
        elif code == "infantry":
            # Добавить пехоту
            wh = next((u for u in self.game.player_units if isinstance(u, Warehouse)), None)
            if wh:
                for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                    nx, ny = wh.x + dx, wh.y + dy
                    cell = self.game.map.get_cell(nx, ny)
                    if cell and cell.is_walkable and not any(u.x == nx and u.y == ny for u in self.game.all_units):
                        inf = Infantry(nx, ny, config.PLAYER, f"Чит-отряд")
                        self.game.all_units.append(inf)
                        self.game.player_units.append(inf)
                        self.game.map.add_unit(inf, nx, ny)
                        self.game.message = "Пехота добавлена"
                        return
            self.game.message = "Нет места для пехоты"
        
        elif code == "tank":
            # Добавить танк
            wh = next((u for u in self.game.player_units if isinstance(u, Warehouse)), None)
            if wh:
                for dx, dy in [(2, 0), (0, 2), (-2, 0), (0, -2)]:
                    nx, ny = wh.x + dx, wh.y + dy
                    cell = self.game.map.get_cell(nx, ny)
                    if cell and cell.is_walkable and not any(u.x == nx and u.y == ny for u in self.game.all_units):
                        tank = Tank(nx, ny, config.PLAYER, f"Чит-танк")
                        self.game.all_units.append(tank)
                        self.game.player_units.append(tank)
                        self.game.map.add_unit(tank, nx, ny)
                        self.game.message = "Танк добавлен"
                        return
            self.game.message = "Нет места для танка"
        
        elif code == "drone":
            # Добавить разведдрон
            wh = next((u for u in self.game.player_units if isinstance(u, Warehouse)), None)
            if wh and wh.batteries >= 5:
                for dx, dy in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                    nx, ny = wh.x + dx, wh.y + dy
                    cell = self.game.map.get_cell(nx, ny)
                    if cell and cell.is_walkable and not any(u.x == nx and u.y == ny for u in self.game.all_units):
                        drone = ReconDrone(nx, ny, config.PLAYER, f"Чит-дрон")
                        self.game.all_units.append(drone)
                        self.game.player_units.append(drone)
                        self.game.map.add_unit(drone, nx, ny)
                        wh.batteries -= 5
                        self.game.message = "Разведдрон добавлен"
                        return
            self.game.message = "Нет батарей или места"
        
        elif code == "resources":
            # Пополнить ресурсы на складе
            wh = next((u for u in self.game.player_units if isinstance(u, Warehouse)), None)
            if wh:
                wh.supplies = wh.max_supplies
                wh.ammo = wh.max_ammo
                wh.fuel = wh.max_fuel
                wh.batteries = wh.max_batteries
                wh.fpv_drones = 10
                self.game.message = "Ресурсы склада пополнены"
            else:
                self.game.message = "Склад не найден"
        
        elif code == "win":
            # Мгновенная победа
            self.game.victory = True
            self.game.game_over = True
            self.game.message = "Победа (чит)"
        
        elif code == "lose":
            # Мгновенное поражение
            self.game.victory = False
            self.game.game_over = True
            self.game.message = "Поражение (чит)"
        
        elif code == "turn":
            # Пропустить 10 ходов
            self.game.turn += 10
            self.game.message = f"Пропущено 10 ходов (текущий: {self.game.turn})"
        
        elif code == "help":
            self.game.message = "Читы: fog, infantry, tank, drone, resources, win, lose, turn"
        
        else:
            self.game.message = f"Неизвестный чит: {cheat_code}"
