import pygame
from .. import config
from ..units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, FPVOperator, ReconOperator, SupplyCache, Artillery, SoldierUnit, RadarEW


class UIPanelRenderer:
    def __init__(self, renderer):
        self.r = renderer

    def _draw_ui_overlay(self, game):
        phase_name = config.PHASE_NAMES.get(game.phase, "?")
        
        # Hot-seat mode: show current player
        if game.game_mode == "hotseat":
            if game.current_player_faction == config.PLAYER:
                player_text = "Ход Игрока 1 (Синие)"
                color = (100, 150, 255)
            else:
                player_text = "Ход Игрока 2 (Красные)"
                color = (255, 100, 100)
            
            player_surf = self.r.font_big.render(player_text, True, color)
            self.r.screen.blit(player_surf, (10, 10))
            
            text = f"Фаза: {phase_name} | Ход: {game.turn}/{game.max_turns}"
            surf = self.r.font_big.render(text, True, (255, 255, 200))
            self.r.screen.blit(surf, (10, 40))
            y_offset = 65
        else:
            text = f"Фаза: {phase_name} | Ход: {game.turn}/{game.max_turns}"
            surf = self.r.font_big.render(text, True, (255, 255, 200))
            self.r.screen.blit(surf, (10, 10))
            y_offset = 35

        # Reinforcement info
        if hasattr(game, 'get_reinforcement_info'):
            info = game.get_reinforcement_info()
            reinf_text = f"Подкрепление: Пехота {info['infantry']} | Танк {info['tank']} | Дрон {info['drone']} | FPV {info['fpv']}"
            reinf_surf = self.r.font_small.render(reinf_text, True, (150, 200, 150))
            self.r.screen.blit(reinf_surf, (10, y_offset))

        if game.selected_unit and game.selected_unit.is_alive:
            unit = game.selected_unit
            px = unit.x * self.r.tsize + self.r.camera_x
            py = unit.y * self.r.tsize + self.r.camera_y
            pygame.draw.rect(self.r.screen, (255, 255, 0, 100),
                             (px - 2, py - 2, self.r.tsize + 4, self.r.tsize + 4), 2)

        if game.radar_mode:
            self._draw_radar(game)

    def _draw_radar(self, game):
        ts = self.r.tsize
        now = pygame.time.get_ticks()
        overlay = pygame.Surface((config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)

        # Collect radar sources (player ReconOperator/ReconDrone)
        sources = [u for u in game.player_units
                   if getattr(u, 'is_radar_source', False) and u.is_alive]

        # Collect all unit positions within radar range
        radar_contacts = set()
        for src in sources:
            for u in game.all_units:
                if not u.is_alive:
                    continue
                dist = abs(src.x - u.x) + abs(src.y - u.y)
                if dist <= config.RADAR_RANGE:
                    radar_contacts.add((u.x, u.y, u.faction))

        for src in sources:
            sx, sy = src.x * ts + self.r.camera_x + ts // 2, src.y * ts + self.r.camera_y + ts // 2
            # Animated radar waves (3 expanding rings)
            for i in range(3):
                phase = (now / 1000.0 * config.RADAR_WAVE_SPEED + i * 0.33) % 1.0
                radius = int(phase * config.RADAR_RANGE * ts)
                alpha = max(0, int(80 * (1 - phase)))
                color = (0, 200, 100, alpha) if src.faction == config.PLAYER else (200, 100, 0, alpha)
                pygame.draw.circle(overlay, color, (sx, sy), radius, max(1, ts // 16))

            # Radar blips for contacts
            for cx, cy, faction in radar_contacts:
                bx = cx * ts + self.r.camera_x + ts // 2
                by = cy * ts + self.r.camera_y + ts // 2
                blip_color = (0, 255, 0, 200) if faction == config.PLAYER else (255, 50, 50, 200)
                pygame.draw.circle(overlay, blip_color, (bx, by), max(3, ts // 6))
                pygame.draw.circle(overlay, (255, 255, 255, 100), (bx, by), max(5, ts // 4), 1)

        self.r.screen.blit(overlay, (0, 0))

        # Indicator
        ind = self.r.font_big.render("РЕЖИМ РАДАРА", True, (0, 255, 100))
        self.r.screen.blit(ind, (10, 40))

    def _draw_resource_buttons(self, game, unit, panel_x, y):
        """Отрисовка ресурсов юнита как кнопок для передачи"""
        from ..units import Infantry, Tank, ReconOperator, FPVOperator, SupplyTruck, Warehouse, SupplyCache, SoldierUnit
        
        # Получаем ресурсы юнита
        resources = []
        
        if isinstance(unit, Infantry):
            total_food = sum(s.food for s in unit.alive_soldiers)
            total_ammo = sum(s.ammo for s in unit.alive_soldiers)
            max_food = len(unit.alive_soldiers) * config.SOLDIER_MAX_FOOD
            max_ammo = len(unit.alive_soldiers) * config.SOLDIER_MAX_AMMO
            resources.append(("📦", "Еда", total_food, max_food, "food"))
            resources.append(("💥", "Боезапас", total_ammo, max_ammo, "ammo"))
            resources.append(("👥", "Люди", unit.soldiers, unit.max_soldiers, "soldiers"))
            cell = game.map.get_cell(unit.x, unit.y)
            resources.append(("🛡", "Укреп", cell.entrenchment, 100, "entrench"))
            resources.append(("😊", "Мораль", unit.morale, 100, "morale"))
            
        elif isinstance(unit, Tank):
            resources.append(("💥", "Снаряды", unit.ammo, unit.max_ammo, "ammo"))
            resources.append(("⛽", "Топливо", unit.fuel, unit.max_fuel, "fuel"))
            resources.append(("📦", "Еда", unit.carry_food, unit.max_carry_food, "food"))
            resources.append(("👥", "Экипаж", unit.crew, unit.max_crew, "crew"))
            resources.append(("🛡", "Броня", unit.armor, unit.max_armor, "armor"))
            
        elif isinstance(unit, ReconOperator):
            drone_active = unit.drone and unit.drone.is_alive
            resources.append(("🚁", "Дрон в запасе", unit.drone_stored, unit.max_drone_stored, "drone_stored"))
            resources.append(("🔋", "Батареи", unit.batteries, unit.max_batteries, "batteries"))
            resources.append(("📦", "Еда", unit.food, unit.max_food, "food"))
            resources.append(("💥", "Боезапас", unit.ammo, unit.max_ammo, "ammo"))
            resources.append(("👥", "Экипаж", unit.crew, unit.max_soldiers, "crew"))
            
        elif isinstance(unit, FPVOperator):
            resources.append(("🎯", "FPV", unit.fpv_stock, unit.max_stock, "fpv"))
            resources.append(("📦", "Еда", unit.food, unit.max_food, "food"))
            resources.append(("💥", "Боезапас", unit.ammo, unit.max_ammo, "ammo"))
            resources.append(("👥", "Экипаж", unit.crew, unit.max_soldiers, "crew"))
            
        elif isinstance(unit, SupplyTruck):
            # === Свои ресурсы (информация) ===
            crew_food = sum(s.food for s in unit.alive_soldiers)
            resources.append(("⛽", "Топливо", unit.fuel, unit.max_fuel, "fuel"))
            resources.append(("🍞", "Еда экип.", crew_food, 100, "crew_food"))
            resources.append(("👥", "Экипаж", unit.crew, unit.max_soldiers, "crew"))
            
        elif isinstance(unit, Warehouse):
            resources.append(("📦", "Припасы", unit.supplies, unit.max_supplies, "supplies"))
            resources.append(("💥", "Боезапас", unit.ammo, unit.max_ammo, "ammo"))
            resources.append(("⛽", "Топливо", unit.fuel, unit.max_fuel, "fuel"))
            resources.append(("🔋", "Батареи", unit.batteries, unit.max_batteries, "batteries"))
            resources.append(("🎯", "FPV", unit.fpv_drones, 10, "fpv"))
            if hasattr(unit, 'recon_drones'):
                resources.append(("🚁", "Разведдроны", unit.recon_drones, 5, "recon_drones"))
            
        elif isinstance(unit, SupplyCache):
            if unit.build_turns < unit.build_required:
                # Показываем прогресс строительства
                progress = unit.build_turns / unit.build_required
                bar_w = config.PANEL_WIDTH - 30
                pygame.draw.rect(self.r.screen, (50, 50, 50), (panel_x + 10, y, bar_w, 12))
                pygame.draw.rect(self.r.screen, (200, 180, 50), (panel_x + 10, y, int(bar_w * progress), 12))
                build_text = self.r.font_small.render(f"Строительство: {unit.build_turns}/{unit.build_required}", True, (255, 255, 200))
                self.r.screen.blit(build_text, (panel_x + 10, y + 14))
                return y + 30
            else:
                resources.append(("📦", "Припасы", unit.supplies, unit.max_supplies, "supplies"))
                resources.append(("💥", "Боезапас", unit.ammo, unit.max_ammo, "ammo"))
                resources.append(("⛽", "Топливо", unit.fuel, unit.max_fuel, "fuel"))
                resources.append(("🔋", "Батареи", unit.batteries, unit.max_batteries, "batteries"))
                resources.append(("🎯", "FPV", unit.fpv_drones, 10, "fpv"))
                if hasattr(unit, 'recon_drones'):
                    resources.append(("🚁", "Разведдроны", unit.recon_drones, 5, "recon_drones"))
                resources.append(("⊞", "Места", unit.used_slots, unit.max_slots, "slots"))
                if unit.garrison > 0:
                    resources.append(("🚪", "Гарнизон", unit.garrison, 5, "garrison"))
                    
        elif isinstance(unit, SoldierUnit):
            s = unit.soldier
            resources.append(("📦", "Еда", s.food, s.max_food, "food"))
            resources.append(("💥", "Боезапас", s.ammo, s.max_ammo, "ammo"))
            resources.append(("❤", "Здоровье", s.health, 100, "health"))
            resources.append(("😊", "Мораль", s.morale, 100, "morale"))
            
        elif isinstance(unit, ReconDrone):
            resources.append(("🔋", "Батарея", unit.battery, unit.max_battery, "battery"))
            resources.append(("👁", "Обзор", unit.vision_range, 10, "vision"))
            
        elif isinstance(unit, Artillery):
            total_food = sum(s.food for s in unit.alive_soldiers)
            max_food = sum(s.max_food for s in unit.alive_soldiers) if unit.alive_soldiers else 0
            resources.append(("💥", "Снаряды", unit.ammo, unit.max_ammo, "ammo"))
            resources.append(("📦", "Еда", total_food, max_food, "food"))
            resources.append(("👥", "Расчёт", unit.crew, unit.max_crew, "crew"))
            cell = game.map.get_cell(unit.x, unit.y)
            resources.append(("🛡", "Укреп", cell.entrenchment, 100, "entrench"))

        elif isinstance(unit, RadarEW):
            resources.append(("📡", "РЭБ", unit.jam_range, 20, "jam_range"))
            resources.append(("⛽", "Топливо", unit.fuel, unit.max_fuel, "fuel"))
            resources.append(("👥", "Экипаж", unit.crew, unit.max_crew, "crew"))
        
        # Рисуем кнопки ресурсов
        btn_h = 20
        btn_w = (config.PANEL_WIDTH - 30) // 2  # Две колонки
        col = 0
        
        for icon, name, value, max_val, res_type in resources:
            bx = panel_x + 10 + col * (btn_w + 5)
            btn_rect = pygame.Rect(bx, y, btn_w, btn_h)
            
            # Цвет кнопки в зависимости от заполненности
            pct = value / max_val if max_val > 0 else 0
            if pct > 0.7:
                bg_color = (40, 80, 40)
                border_color = (60, 120, 60)
                text_color = (150, 255, 150)
            elif pct > 0.3:
                bg_color = (80, 80, 40)
                border_color = (120, 120, 60)
                text_color = (255, 255, 150)
            else:
                bg_color = (80, 40, 40)
                border_color = (120, 60, 60)
                text_color = (255, 150, 150)
            
            # Проверяем наведение
            mx, my = pygame.mouse.get_pos()
            if btn_rect.collidepoint(mx, my):
                bg_color = (min(255, bg_color[0] + 20), min(255, bg_color[1] + 20), min(255, bg_color[2] + 20))
            
            pygame.draw.rect(self.r.screen, bg_color, btn_rect, border_radius=2)
            pygame.draw.rect(self.r.screen, border_color, btn_rect, 1, border_radius=2)
            
            # Текст кнопки
            btn_text = f"{icon} {name}: {value}"
            btn_surf = self.r.font_small.render(btn_text, True, text_color)
            self.r.screen.blit(btn_surf, (bx + 4, y + 3))
            
            # Сохраняем rect для обработки кликов
            self.r.action_buttons_rects.append((btn_rect, f"resource_{res_type}"))
            
            col += 1
            if col >= 2:
                col = 0
                y += btn_h + 3
        
        if col > 0:
            y += btn_h + 3
        
        return y

    def _draw_right_panel(self, game):
        panel_x = config.SCREEN_WIDTH - config.PANEL_WIDTH
        panel_rect = pygame.Rect(panel_x, 0, config.PANEL_WIDTH, config.SCREEN_HEIGHT)
        pygame.draw.rect(self.r.screen, (30, 30, 40), panel_rect)
        pygame.draw.line(self.r.screen, (80, 80, 80), (panel_x, 0),
                         (panel_x, config.SCREEN_HEIGHT), 2)

        # Fixed combat log zone at bottom
        combat_log_bottom = config.SCREEN_HEIGHT - 4
        combat_log_top = combat_log_bottom - 82  # header + 4 entries + padding
        # Clip area for everything above combat log
        clip_above = pygame.Rect(panel_x, 0, config.PANEL_WIDTH, combat_log_top)
        self.r.screen.set_clip(clip_above)

        y = 15
        self.r.action_buttons_rects = []
        title = self.r.font_title.render("УПРАВЛЕНИЕ", True, (200, 200, 255))
        self.r.screen.blit(title, (panel_x + 10, y))
        y += 25
        
        # ESP menu hint
        esp_hint = self.r.font_small.render("Tab - ESP меню", True, (100, 180, 255))
        self.r.screen.blit(esp_hint, (panel_x + 10, y))
        y += 18
        
        # Hourglass button
        self._draw_hourglass_button(game, panel_x, y)
        y += 65
        
        unit = game.selected_unit
        if unit and unit.is_alive:
            name = self.r.font_big.render(unit.name, True, (255, 255, 255))
            self.r.screen.blit(name, (panel_x + 10, y))
            y += 25

            # Soldier management mode: show soldier list or detail
            if game.soldier_management_mode and game.soldier_source_unit is unit:
                if game.soldier_detail_idx is not None:
                    self._draw_soldier_detail(game, panel_x, y, combat_log_top)
                else:
                    self._draw_soldier_list(game, panel_x, y, combat_log_top)
                y = combat_log_top + 1
            else:
                # Отрисовка ресурсов как кнопок
                y = self._draw_resource_buttons(game, unit, panel_x, y)

            if not isinstance(unit, SupplyCache):
                # Отображение очков движения
                max_move = game.get_unit_max_move(unit)
                max_steps = game.get_unit_max_steps(unit)
                if not unit.moved:
                    mv = self.r.font_small.render(f"ОД: {max_move} | Шагов: {max_steps}", True, (100, 200, 100))
                else:
                    mv = self.r.font_small.render("Ход завершён", True, (200, 100, 100))
                self.r.screen.blit(mv, (panel_x + 10, y))
                y += 16

            if not isinstance(unit, SupplyCache) and not game.soldier_management_mode:
                if not unit.attacked and hasattr(unit, 'ammo') and unit.ammo > 0:
                    at = self.r.font_small.render("Может атаковать", True, (100, 200, 100))
                else:
                    at = self.r.font_small.render("Атаковал или нет боезапаса", True, (200, 100, 100))
                self.r.screen.blit(at, (panel_x + 10, y))
                y += 18

            if not game.soldier_management_mode:
                y += 5
                self._draw_action_buttons(game, panel_x, y)
        elif game.pinned_cell:
            gx, gy = game.pinned_cell
            cell = game.map.get_cell(gx, gy)
            if cell:
                title = self.r.font_big.render(f"Клетка ({gx}, {gy})", True, (255, 255, 200))
                self.r.screen.blit(title, (panel_x + 10, y))
                y += 25
                terr = self.r.font_normal.render(f"Тип: {cell.name}", True, (200, 200, 200))
                self.r.screen.blit(terr, (panel_x + 10, y))
                y += 20
                if cell.visible:
                    terr_def = self.r.font_small.render(f"Бонус обороны: {cell.defense_bonus}%", True, (180, 180, 180))
                    self.r.screen.blit(terr_def, (panel_x + 10, y))
                    y += 16
                    terr_cover = self.r.font_small.render(f"Укрытие: {cell.cover_bonus}%", True, (180, 180, 180))
                    self.r.screen.blit(terr_cover, (panel_x + 10, y))
                    y += 16
                if cell.units:
                    for u in cell.units:
                        if not u.is_alive:
                            continue
                        if u.faction == config.ENEMY and not cell.visible:
                            continue
                        faction_tag = " [ВРАГ]" if u.faction == config.ENEMY else ""
                        color = (255, 100, 100) if u.faction == config.ENEMY else (100, 200, 100)
                        ulabel = self.r.font_small.render(f"{u.name}{faction_tag}", True, color)
                        self.r.screen.blit(ulabel, (panel_x + 10, y))
                        y += 14
                        if isinstance(u, Infantry):
                            self.r.screen.blit(self.r.font_small.render(f"  Солдаты: {u.soldiers}/{u.max_soldiers}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Укрепление: {cell.entrenchment}%", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Защита от дронов: 15% (сбитие)", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Защита от пехоты: {cell.defense_bonus}% террейн", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Защита от техники: {cell.defense_bonus}% террейн", True, (200,200,200)), (panel_x + 15, y)); y += 13
                        elif isinstance(u, Tank):
                            self.r.screen.blit(self.r.font_small.render(f"  Экипаж: {u.crew}/{u.max_crew}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Броня: {u.armor}/{u.max_armor}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Защита от дронов: 20% (РЭБ)", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Защита от пехоты: {cell.defense_bonus}% террейн", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Броня от техники: {u.armor//10}% поглощение", True, (200,200,200)), (panel_x + 15, y)); y += 13
                        elif isinstance(u, ReconDrone):
                            self.r.screen.blit(self.r.font_small.render(f"  Батарея: {u.battery}/{u.max_battery}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Обзор: {u.vision_range} кл.", True, (200,200,200)), (panel_x + 15, y)); y += 13
                        elif isinstance(u, Warehouse):
                            self.r.screen.blit(self.r.font_small.render(f"  Припасы: {u.supplies}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Боезапас: {u.ammo}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                            self.r.screen.blit(self.r.font_small.render(f"  Батареи: {u.batteries}", True, (200,200,200)), (panel_x + 15, y)); y += 13
                        y += 4
                else:
                    empty = self.r.font_normal.render("Нет юнитов", True, (150, 150, 150))
                    self.r.screen.blit(empty, (panel_x + 10, y))
        else:
            y += 40
            hint = self.r.font_normal.render("Кликните на юните", True, (150, 150, 150))
            self.r.screen.blit(hint, (panel_x + 10, y))
            y += 25
            
            # Unit counts with icons
            self._draw_troops_icons(game, panel_x, y, max_y=combat_log_top)
            y += 25
            
            # Warehouse supplies with icons
            for u in game.player_units:
                if isinstance(u, Warehouse) and u.is_alive:
                    wh_text = self.r.font_small.render(f"Склад: 📦{u.supplies} 💥{u.ammo} ⛽{u.fuel} 🔋{u.batteries}", True, (200, 200, 200))
                    self.r.screen.blit(wh_text, (panel_x + 10, y))
                    y += 16
                    break
            
            # Day speed and reinforcement info
            y += 5
            min_reinf = min(game.reinforcement_timers.values()) if game.reinforcement_timers else 0
            stats_text = self.r.font_small.render(f"День: {game.turn} | Юнитов: {len([u for u in game.player_units if u.is_alive])}", True, (180, 180, 180))
            self.r.screen.blit(stats_text, (panel_x + 10, y))
            y += 14
            reinf_text = self.r.font_small.render(f"Пополнение через: {min_reinf} ходов", True, (150, 200, 150))
            self.r.screen.blit(reinf_text, (panel_x + 10, y))
            y += 20
            
            # Доступность ходов у юнитов
            move_header = self.r.font_small.render("Доступность ходов:", True, (200, 200, 100))
            self.r.screen.blit(move_header, (panel_x + 10, y))
            y += 14
            
            for u in game.player_units:
                if not u.is_alive or isinstance(u, (Warehouse, SupplyCache)):
                    continue
                max_move = game.get_unit_max_move(u)
                max_steps = game.get_unit_max_steps(u)
                can_move = not u.moved
                can_attack = not u.attacked and hasattr(u, 'ammo') and u.ammo > 0
                
                # Цвет индикатора
                if can_move and can_attack:
                    status_color = (100, 200, 100)  # Зелёный - всё доступно
                    status_icon = "●"
                elif can_move:
                    status_color = (200, 200, 100)  # Жёлтый - только движение
                    status_icon = "◐"
                elif can_attack:
                    status_color = (200, 150, 50)  # Оранжевый - только атака
                    status_icon = "◑"
                else:
                    status_color = (150, 50, 50)  # Красный - всё использовано
                    status_icon = "○"
                
                # Сокращённое имя
                name_short = u.name[:10]
                unit_text = f"{status_icon} {name_short} {max_steps}ш/{max_move}ОД"
                unit_surf = self.r.font_small.render(unit_text, True, status_color)
                if y + 12 < combat_log_top:
                    self.r.screen.blit(unit_surf, (panel_x + 10, y))
                    y += 12

        # Restore clip and draw combat log at fixed bottom
        self.r.screen.set_clip(None)

        # Icon-based troops display (below clip area)
        troops_y = combat_log_top - 20
        self._draw_troops_icons(game, panel_x, troops_y, max_y=combat_log_top)

        clog = self.r.font_normal.render("БОЕВОЙ ЖУРНАЛ:", True, (200, 200, 100))
        self.r.screen.blit(clog, (panel_x + 10, combat_log_top + 2))
        ly = combat_log_top + 22
        for i, entry in enumerate(game.combat_log[-4:]):
            msg = entry.get("message", "")[:35]
            esurf = self.r.font_small.render(msg, True, (200, 200, 200))
            self.r.screen.blit(esurf, (panel_x + 10, ly))
            ly += 14

    def _draw_troops_icons(self, game, panel_x, y, max_y=None):
        """Отрисовка войск иконками"""
        # Считаем количество юнитов по типам
        infantry_count = 0
        tank_count = 0
        drone_count = 0
        truck_count = 0
        
        for u in game.player_units:
            if not u.is_alive:
                continue
            if isinstance(u, Infantry):
                infantry_count += 1
            elif isinstance(u, Tank):
                tank_count += 1
            elif isinstance(u, ReconDrone):
                drone_count += 1
            elif isinstance(u, SupplyTruck):
                truck_count += 1
        
        # Рисуем иконки
        icon_size = 16
        x_offset = panel_x + 10
        
        # Пехота
        if infantry_count > 0:
            self._draw_infantry_icon(x_offset, y, icon_size, (100, 150, 255))
            count_surf = self.r.font_small.render(str(infantry_count), True, (200, 200, 200))
            self.r.screen.blit(count_surf, (x_offset + icon_size + 3, y + 2))
            x_offset += 40
        
        # Танки
        if tank_count > 0:
            self._draw_tank_icon(x_offset, y, icon_size, (100, 200, 100))
            count_surf = self.r.font_small.render(str(tank_count), True, (200, 200, 200))
            self.r.screen.blit(count_surf, (x_offset + icon_size + 3, y + 2))
            x_offset += 40
        
        # Дроны
        if drone_count > 0:
            self._draw_drone_icon(x_offset, y, icon_size, (50, 180, 220))
            count_surf = self.r.font_small.render(str(drone_count), True, (200, 200, 200))
            self.r.screen.blit(count_surf, (x_offset + icon_size + 3, y + 2))
            x_offset += 40
        
        # Грузовики
        if truck_count > 0:
            self._draw_truck_icon(x_offset, y, icon_size, (200, 180, 50))
            count_surf = self.r.font_small.render(str(truck_count), True, (200, 200, 200))
            self.r.screen.blit(count_surf, (x_offset + icon_size + 3, y + 2))
    
    def _draw_infantry_icon(self, x, y, size, color):
        """Маленькая иконка пехоты"""
        # Человечек
        r = size // 4
        cx, cy = x + size // 2, y + size // 2
        pygame.draw.circle(self.r.screen, color, (cx, cy - r), r)
        pygame.draw.circle(self.r.screen, (0, 0, 0), (cx, cy - r), r, 1)
        # Тело
        pygame.draw.line(self.r.screen, color, (cx, cy), (cx, cy + r * 2), 2)
        # Руки
        pygame.draw.line(self.r.screen, color, (cx - r, cy + r), (cx + r, cy + r), 1)
        # Ноги
        pygame.draw.line(self.r.screen, color, (cx, cy + r * 2), (cx - r, cy + r * 3), 1)
        pygame.draw.line(self.r.screen, color, (cx, cy + r * 2), (cx + r, cy + r * 3), 1)
    
    def _draw_tank_icon(self, x, y, size, color):
        """Маленькая иконка танка"""
        # Корпус
        body = pygame.Rect(x + 2, y + size // 3, size - 4, size // 3)
        pygame.draw.rect(self.r.screen, color, body)
        pygame.draw.rect(self.r.screen, (0, 0, 0), body, 1)
        # Башня
        turret = pygame.Rect(x + size // 3, y + size // 4, size // 3, size // 4)
        pygame.draw.ellipse(self.r.screen, color, turret)
        pygame.draw.ellipse(self.r.screen, (0, 0, 0), turret, 1)
        # Ствол
        barrel = pygame.Rect(x + size * 2 // 3, y + size // 3, size // 4, 2)
        pygame.draw.rect(self.r.screen, (80, 80, 80), barrel)
    
    def _draw_drone_icon(self, x, y, size, color):
        """Маленькая иконка дрона"""
        cx, cy = x + size // 2, y + size // 2
        off = size // 4
        w = max(1, size // 8)
        # Крестовина
        pygame.draw.line(self.r.screen, color, (cx - off, cy - off), (cx + off, cy + off), w)
        pygame.draw.line(self.r.screen, color, (cx + off, cy - off), (cx - off, cy + off), w)
        # Центр
        pygame.draw.circle(self.r.screen, (200, 200, 255), (cx, cy), max(2, size // 5))
    
    def _draw_truck_icon(self, x, y, size, color):
        """Маленькая иконка грузовика"""
        # Кабина
        cab_w = size // 3
        cab_h = size // 2
        pygame.draw.rect(self.r.screen, (80, 80, 80), (x + 1, y + size - cab_h - 2, cab_w, cab_h))
        # Кузов
        cargo_w = size // 2
        cargo_h = size * 2 // 3
        pygame.draw.rect(self.r.screen, color, (x + cab_w, y + size - cargo_h - 2, cargo_w, cargo_h))
        # Колёса
        r = max(1, size // 8)
        pygame.draw.circle(self.r.screen, (40, 40, 40), (x + cab_w // 2, y + size - 2), r)
        pygame.draw.circle(self.r.screen, (40, 40, 40), (x + cab_w + cargo_w // 2, y + size - 2), r)

    def _draw_troops_summary(self, game, panel_x, y, max_y=None):
        title = self.r.font_normal.render("СВОЙСКА:", True, (200, 200, 100))
        self.r.screen.blit(title, (panel_x + 10, y))
        y += 18
        combat_units = []
        support_units = []
        for u in game.player_units:
            if not u.is_alive:
                continue
            if isinstance(u, (Infantry, Tank)):
                combat_units.append(u)
            else:
                support_units.append(u)

        for u in combat_units:
            if max_y and y + 14 > max_y:
                return y
            if isinstance(u, Infantry):
                total_food = u.total_food_carried
                total_ammo = sum(s.ammo for s in u.alive_soldiers)
                load_str = f" [ПЕРЕГРУЗ]" if u.is_overloaded else ""
                cell = game.map.get_cell(u.x, u.y)
                line = f"{u.name[:10]}: {u.soldiers}чл, {total_food}/{u.carry_capacity}ед, {total_ammo}бз, укр{cell.entrenchment}%{load_str}"
            elif isinstance(u, Tank):
                carry_str = ""
                if u.carry_food > 0 or u.carry_ammo > 0:
                    carry_str = f", груз еда{u.carry_food}/бз{u.carry_ammo}"
                line = f"{u.name[:10]}: {u.crew}эк, {u.armor}бр, {u.ammo}сн, {u.fuel}топ{carry_str}"
            lsurf = self.r.font_small.render(line, True, (180, 220, 180))
            self.r.screen.blit(lsurf, (panel_x + 10, y))
            y += 14

        for u in support_units:
            if max_y and y + 14 > max_y:
                return y
            if isinstance(u, ReconDrone):
                line = f"{u.name[:10]}: бат {u.battery}/{u.max_battery}, обз {u.vision_range}"
            elif isinstance(u, ReconOperator):
                line = f"{u.name[:10]}: батарей {u.batteries}"
            elif isinstance(u, FPVOperator):
                line = f"{u.name[:10]}: FPV {u.fpv_stock}/{u.max_stock}"
            elif isinstance(u, SupplyTruck):
                line = f"{u.name[:10]}: вес {u.total_weight}/{u.max_weight}, топл {u.fuel}"
            elif isinstance(u, Warehouse):
                line = f"{u.name[:10]}: прип {u.supplies}, бз {u.ammo}, бат {u.batteries}"
            elif isinstance(u, SupplyCache):
                if u.build_turns < u.build_required:
                    line = f"{u.name[:10]}: стройка {u.build_turns}/{u.build_required}"
                else:
                    line = f"{u.name[:10]}: пр {u.supplies}, бз {u.ammo}, т {u.fuel}"
            else:
                continue
            lsurf = self.r.font_small.render(line, True, (180, 180, 200))
            self.r.screen.blit(lsurf, (panel_x + 10, y))
            y += 14
        return y

    def _draw_action_buttons(self, game, panel_x, y):
        unit = game.selected_unit
        if not unit:
            return

        # Не очищаем action_buttons_rects если уже есть кнопки ресурсов
        if not hasattr(self.r, 'action_buttons_rects'):
            self.r.action_buttons_rects = []
        
        buttons = []
        has_crew = hasattr(unit, 'soldiers_list')
        
        # Отображение очков движения для всех юнитов
        if not isinstance(unit, (SupplyCache, Warehouse)):
            max_move = game.get_unit_max_move(unit)
            max_steps = game.get_unit_max_steps(unit)
            if not unit.moved:
                move_text = f"ОД: {max_move} | Шагов: {max_steps}"
            else:
                move_text = "Ход завершён"
            buttons.append(("▶", move_text, None))
        
        if isinstance(unit, SoldierUnit):
            # Кнопки для одиночного бойца
            if not unit.moved:
                buttons.append(("▶", "Движение", None))
            # Кнопка "Присоединиться к отряду"
            has_nearby_squad = any(
                isinstance(u, Infantry) and u.is_alive and u.faction == unit.faction and
                abs(u.x - unit.x) + abs(u.y - unit.y) <= 1 and len(u.alive_soldiers) < u.max_soldiers
                for u in game.all_units
            )
            buttons.append(("⊕→", "Идти и присоединиться", "join_squad_move"))
            # Кнопка "Организовать отделение"
            has_nearby_soldier = any(
                isinstance(u, SoldierUnit) and u.is_alive and u is not unit and u.faction == unit.faction and
                abs(u.x - unit.x) + abs(u.y - unit.y) <= 1
                for u in game.all_units
            )
            if has_nearby_soldier:
                buttons.append(("⊕", "Организовать отделение", "form_squad"))
            # Кнопка "Погрузиться в грузовик"
            cell = game.map.get_cell(unit.x, unit.y)
            has_truck = cell and any(
                isinstance(u, SupplyTruck) and u.is_alive and u.faction == unit.faction
                for u in cell.units
            )
            if has_truck:
                buttons.append(("🚚", "Погрузиться в грузовик", "load_to_truck"))
        
        elif isinstance(unit, (Infantry, Tank)):
            if not unit.moved:
                buttons.append(("▶", "Движение", None))
            if not unit.attacked:
                if isinstance(unit, Infantry):
                    has_ammo = any(s.ammo > 0 for s in unit.alive_soldiers)
                else:
                    has_ammo = hasattr(unit, 'ammo') and unit.ammo > 0
                if has_ammo:
                    buttons.append(("⚔", "Атака", None))
            if isinstance(unit, Infantry):
                if not unit.entrenching:
                    buttons.append(("⛏", "Окопаться", "entrench"))
                if not unit.building_cache:
                    buttons.append(("🏗", "Построить погреб", "build_cache"))
            if isinstance(unit, Infantry):
                has_resources = unit.ammo > 0 or any(s.food > 0 for s in unit.alive_soldiers)
            elif isinstance(unit, Tank):
                has_resources = unit.ammo > 0 or unit.carry_food > 0 or unit.carry_ammo > 0
            else:
                has_resources = hasattr(unit, 'ammo') and unit.ammo > 0
            if has_resources:
                pass  # Ресурсы передаются через кнопки ресурсов выше
        elif isinstance(unit, ReconDrone):
            buttons.append(("👁", f"Обзор {unit.vision_range} кл.", None))
        elif isinstance(unit, Artillery):
            if not unit.moved:
                buttons.append(("▶", "Движение", None))
            has_ammo = unit.ammo > 0
            if has_ammo and not unit.attacked:
                buttons.append(("💥", f"Атака ({unit.attack_range} кл.)", None))
                buttons.append(("🎯", "Обстрел (30 кл.)", "artillery_barrage"))
        elif isinstance(unit, FPVOperator):
            buttons.append(("🎯", f"FPV: {unit.fpv_stock}/{unit.max_stock}", None))
            mode = "Авто" if unit.auto_mode else "Ручной"
            buttons.append(("⟳", f"Режим: {mode}", "toggle_fpv"))
        elif isinstance(unit, ReconOperator):
            drone_active = unit.drone and unit.drone.is_alive
            if unit.drone_stored > 0 and not drone_active:
                buttons.append(("🚁", f"Активировать дрон ({unit.drone_stored})", "deploy_drone"))
            elif drone_active:
                buttons.append(("🚁", "Дрон активен", None))
            else:
                buttons.append(("🚁", "Нет дрона в запасе", None))
            buttons.append(("🔋", f"Батареи: {unit.batteries}/{unit.max_batteries}", None))
            buttons.append(("↓", "Взять батареи", "load_batteries"))
        elif isinstance(unit, RadarEW):
            ew_status = "ВКЛ" if unit.active else "ВЫКЛ"
            buttons.append(("📡", f"РЭБ: {ew_status}", "toggle_ew"))
            buttons.append(("📡", f"Дальность: {unit.jam_range} кл.", None))
            buttons.append(("👥", f"Экипаж: {unit.crew}/{unit.max_crew}", None))
        elif isinstance(unit, SupplyTruck):
            if unit.auto_mix:
                buttons.append(("⟳", "Режим: всё подряд", "toggle_mix"))
            else:
                mode_name = config.CARGO_NAMES.get(unit.current_load_type, unit.current_load_type)
                buttons.append(("⟳", f"Режим: {mode_name}", "toggle_mix"))
            buttons.append(("↓", f"Загрузить", "load"))
            buttons.append(("↑", "Разгрузить", "unload"))
            buttons.append(("🚚", "Доставить юниту", "deliver_to_unit"))
            # Кнопки для дронов (загрузка со склада/погреба)
            cell = game.map.get_cell(unit.x, unit.y)
            if cell:
                supply_source = None
                for u in cell.units:
                    if u.is_alive and u.faction == unit.faction and isinstance(u, (Warehouse, SupplyCache)):
                        if isinstance(u, SupplyCache) and u.build_turns < u.build_required:
                            continue
                        supply_source = u
                        break
                if supply_source:
                    if hasattr(supply_source, 'recon_drones') and supply_source.recon_drones > 0 and unit.cargo.get('recon_drone', 0) < 1:
                        buttons.append(("🚁", "Загрузить разведдрон", "load_recon_drone"))
                    if hasattr(supply_source, 'fpv_drones') and supply_source.fpv_drones > 0:
                        buttons.append(("🎯", "Загрузить FPV-дроны", "load_fpv_drone"))
            # Кнопки доставки дронов операторам
            recon_cargo = unit.cargo.get('recon_drone', 0)
            fpv_cargo = unit.cargo.get('fpv_drone', 0)
            if recon_cargo > 0:
                has_nearby_recon_op = any(
                    isinstance(u, ReconOperator) and u.is_alive and u.faction == unit.faction and
                    abs(u.x - unit.x) + abs(u.y - unit.y) <= 1 and u.drone_stored < u.max_drone_stored
                    for u in game.all_units
                )
                if has_nearby_recon_op:
                    buttons.append(("🚁", "Доставить разведдрон", "deliver_recon_drone"))
            if fpv_cargo > 0:
                has_nearby_fpv_op = any(
                    isinstance(u, FPVOperator) and u.is_alive and u.faction == unit.faction and
                    abs(u.x - unit.x) + abs(u.y - unit.y) <= 1 and u.fpv_stock < u.max_stock
                    for u in game.all_units
                )
                if has_nearby_fpv_op:
                    buttons.append(("🎯", "Доставить FPV-дроны", "deliver_fpv_drone"))
            route = unit.supply_route
            if route:
                buttons.append(("✕", "Остановить маршрут", "cancel_route"))
            else:
                has_origin = hasattr(unit, '_route_origin') and unit._route_origin
                has_dest = hasattr(unit, '_route_dest') and unit._route_dest
                if has_origin and has_dest:
                    buttons.append(("▶", "Начать маршрут", "start_route"))
                else:
                    o_name = "—"
                    d_name = "—"
                    if has_origin:
                        o_name = unit._route_origin.name[:8]
                    if has_dest:
                        d_name = unit._route_dest.name[:8]
                    buttons.append(("📦", f"Склад: {o_name}", "set_origin"))
                    buttons.append(("🎯", f"Погреб: {d_name}", "set_dest"))
            
            # === Груз (кнопки передачи) ===
            buttons.append(None)  # Разделитель
            fill_pct = int(unit.total_weight / unit.max_weight * 100) if unit.max_weight > 0 else 0
            buttons.append(("📦", f"Груз: {unit.total_weight}/{unit.max_weight} кг ({fill_pct}%)", None))
            for ct in SupplyTruck.CARGO_CYCLE:
                val = unit.cargo.get(ct, 0)
                icon = {"supplies": "📦", "ammo": "💥", "fuel": "⛽", "batteries": "🔋", "fpv_drone": "🎯", "recon_drone": "🚁"}.get(ct, "📦")
                name = config.CARGO_NAMES.get(ct, ct)
                buttons.append((icon, f"{name}: {val}", f"cargo_{ct}"))
        elif isinstance(unit, SupplyCache):
            if unit.build_turns < unit.build_required:
                buttons.append(("🔨", f"Строительство: {unit.build_turns}/{unit.build_required}", None))
            else:
                if unit.garrison > 0:
                    buttons.append(("🚪", f"Гарнизон: {unit.garrison}", "exit_garrison"))
        elif isinstance(unit, Warehouse) and unit.faction == config.PLAYER:
            buttons.append(("📦", "Перенести склад", "move_warehouse"))

        if has_crew and not isinstance(unit, Warehouse):
            crew_count = unit.crew if hasattr(unit, 'crew') else unit.soldiers
            if not game.soldier_management_mode:
                buttons.append(("👤", f"Состав ({crew_count}/{unit.max_soldiers})", "soldier_management"))
            else:
                buttons.append(("✖", "Закрыть состав", "soldier_management"))

        for btn in buttons:
            # Разделитель
            if btn is None:
                pygame.draw.line(self.r.screen, (80, 80, 60), (panel_x + 10, y + 3), (panel_x + config.PANEL_WIDTH - 15, y + 3), 1)
                y += 8
                continue
            
            icon, label, action = btn
            btn_rect = pygame.Rect(panel_x + 10, y, config.PANEL_WIDTH - 20, 26)
            self.r.action_buttons_rects.append((btn_rect, action))
            
            # Определяем цвет кнопки
            if action:
                bg_color = (50, 70, 50)
                border_color = (80, 120, 80)
            else:
                bg_color = (60, 60, 80)
                border_color = (100, 100, 120)
            
            # Проверяем наведение
            mx, my = pygame.mouse.get_pos()
            if btn_rect.collidepoint(mx, my):
                bg_color = (70, 90, 70) if action else (80, 80, 100)
            
            pygame.draw.rect(self.r.screen, bg_color, btn_rect, border_radius=3)
            pygame.draw.rect(self.r.screen, border_color, btn_rect, 1, border_radius=3)
            
            # Иконка
            icon_surf = self.r.font_normal.render(icon, True, (200, 200, 200))
            self.r.screen.blit(icon_surf, (panel_x + 15, y + 5))
            
            # Текст
            bsurf = self.r.font_small.render(label, True, (220, 220, 220))
            self.r.screen.blit(bsurf, (panel_x + 35, y + 6))
            
            y += 29

    def _draw_soldier_list(self, game, panel_x, start_y, max_y):
        """Список солдат в пехотном отряде с иконками и характеристиками"""
        self.r.soldier_rects = []
        unit = game.soldier_source_unit
        if not unit or not unit.is_alive:
            return

        soldiers = unit.alive_soldiers
        if not soldiers:
            self.r.screen.blit(self.r.font_small.render("Нет живых солдат", True, (200, 100, 100)), (panel_x + 10, start_y))
            return

        y = start_y
        unit_type = "Состав"
        if hasattr(unit, 'soldiers_list'):
            from ..units import Tank, Artillery, FPVOperator, Infantry, RadarEW
            if isinstance(unit, Tank):
                unit_type = "Экипаж танка"
            elif isinstance(unit, Artillery):
                unit_type = "Расчёт артиллерии"
            elif isinstance(unit, FPVOperator):
                unit_type = "Расчёт FPV"
            elif isinstance(unit, Infantry):
                unit_type = "Отряд"
            elif isinstance(unit, RadarEW):
                unit_type = "Экипаж РЭБ"
        header = self.r.font_small.render(f"{unit_type}: {len(soldiers)}/{unit.max_soldiers}", True, (200, 200, 100))
        self.r.screen.blit(header, (panel_x + 10, y))
        y += 18

        if game.soldier_transfer_mode:
            transfer_hint = self.r.font_small.render("Кликните на отряд для перевода (ESC-отмена)", True, (255, 200, 50))
            self.r.screen.blit(transfer_hint, (panel_x + 10, y))
            y += 16

        for idx, soldier in enumerate(soldiers):
            if y + 42 > max_y:
                more = self.r.font_small.render(f"...ещё {len(soldiers) - idx} солдат", True, (150, 150, 150))
                self.r.screen.blit(more, (panel_x + 10, y))
                break

            is_selected = game.selected_soldier_idx == idx
            row_rect = pygame.Rect(panel_x + 5, y, config.PANEL_WIDTH - 10, 40)
            self.r.soldier_rects.append((idx, row_rect))

            # Фон строки
            mx, my = pygame.mouse.get_pos()
            hover = row_rect.collidepoint(mx, my)
            if is_selected:
                bg = (60, 80, 40)
            elif hover:
                bg = (50, 50, 65)
            else:
                bg = (40, 40, 55)
            pygame.draw.rect(self.r.screen, bg, row_rect, border_radius=3)
            pygame.draw.rect(self.r.screen, (80, 80, 100), row_rect, 1, border_radius=3)

            # Иконка солдата (человечек)
            icon_x = panel_x + 10
            icon_y = y + 4
            icon_color = (150, 200, 255) if not soldier.gender == "female" else (255, 170, 200)
            # Голова
            pygame.draw.circle(self.r.screen, icon_color, (icon_x + 6, icon_y + 5), 4)
            pygame.draw.circle(self.r.screen, (0, 0, 0), (icon_x + 6, icon_y + 5), 4, 1)
            # Тело
            pygame.draw.line(self.r.screen, icon_color, (icon_x + 6, icon_y + 9), (icon_x + 6, icon_y + 18), 2)
            # Руки
            pygame.draw.line(self.r.screen, icon_color, (icon_x + 1, icon_y + 13), (icon_x + 11, icon_y + 13), 1)
            # Ноги
            pygame.draw.line(self.r.screen, icon_color, (icon_x + 6, icon_y + 18), (icon_x + 2, icon_y + 24), 1)
            pygame.draw.line(self.r.screen, icon_color, (icon_x + 6, icon_y + 18), (icon_x + 10, icon_y + 24), 1)

            # Имя и фамилия
            name_text = soldier.full_name
            name_surf = self.r.font_small.render(name_text, True, (220, 220, 220))
            self.r.screen.blit(name_surf, (panel_x + 22, y + 2))

            # Роль (если есть)
            role_text = getattr(soldier, 'role', '')
            if role_text and role_text != "Солдат":
                role_surf = self.r.font_small.render(f"[{role_text}]", True, (180, 160, 120))
                self.r.screen.blit(role_surf, (panel_x + 22 + name_surf.get_width() + 4, y + 2))

            # Навыки (сокращённо)
            skills_text = ", ".join(soldier.skills[:3])
            if len(soldier.skills) > 3:
                skills_text += f" +{len(soldier.skills)-3}"
            skills_surf = self.r.font_small.render(skills_text, True, (160, 180, 200))
            self.r.screen.blit(skills_surf, (panel_x + 22, y + 15))

            # Полоска HP
            hp_bar_x = panel_x + config.PANEL_WIDTH - 80
            hp_bar_w = 55
            hp_bar_h = 5
            hp_bar_y = y + 5
            pygame.draw.rect(self.r.screen, (60, 40, 40), (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h))
            hp_pct = soldier.health / 100.0
            hp_color = (50, 200, 50) if hp_pct > 0.5 else (200, 200, 50) if hp_pct > 0.25 else (200, 50, 50)
            pygame.draw.rect(self.r.screen, hp_color, (hp_bar_x, hp_bar_y, int(hp_bar_w * hp_pct), hp_bar_h))

            # Полоска морали
            morale_bar_y = y + 14
            pygame.draw.rect(self.r.screen, (60, 40, 60), (hp_bar_x, morale_bar_y, hp_bar_w, hp_bar_h))
            morale_pct = soldier.morale / 100.0
            morale_color = (100, 150, 255) if morale_pct > 0.5 else (200, 150, 50) if morale_pct > 0.25 else (200, 50, 80)
            pygame.draw.rect(self.r.screen, morale_color, (hp_bar_x, morale_bar_y, int(hp_bar_w * morale_pct), hp_bar_h))

            # Опыт и значение
            exp_text = f"Еда:{soldier.food}/{soldier.max_food} Б/з:{soldier.ammo}/{soldier.max_ammo}"
            exp_surf = self.r.font_small.render(exp_text, True, (140, 140, 160))
            self.r.screen.blit(exp_surf, (panel_x + 22, y + 28))

            # Индикатор ранения
            if soldier.wound_level > 0:
                wound_colors = {1: (255, 255, 100), 2: (255, 165, 0), 3: (255, 50, 50)}
                wound_names = {1: "Л", 2: "С", 3: "Т"}  # Лёгкое/Среднее/Тяжёлое
                wound_color = wound_colors.get(soldier.wound_level, (200, 200, 200))
                wound_text = wound_names.get(soldier.wound_level, "?")
                wound_surf = self.r.font_small.render(f"[{wound_text}]", True, wound_color)
                self.r.screen.blit(wound_surf, (panel_x + 22 + len(exp_text) * 4, y + 28))

            # HP и мораль цифрами
            hp_val = self.r.font_small.render(f"{soldier.health}%", True, hp_color)
            self.r.screen.blit(hp_val, (hp_bar_x + hp_bar_w + 3, y + 3))
            morale_val = self.r.font_small.render(f"{soldier.morale}%", True, morale_color)
            self.r.screen.blit(morale_val, (hp_bar_x + hp_bar_w + 3, y + 12))

            # Индикатор перевода
            if is_selected and game.soldier_transfer_mode:
                pygame.draw.rect(self.r.screen, (255, 200, 50), row_rect, 2, border_radius=3)

            y += 42

    def _draw_soldier_detail(self, game, panel_x, start_y, max_y):
        """Детальный просмотр одного солдата"""
        self.r.soldier_detail_rects = []
        unit = game.soldier_source_unit
        soldier_idx = game.soldier_detail_idx
        if not unit or not unit.is_alive or soldier_idx is None:
            return

        soldiers = unit.alive_soldiers
        if soldier_idx >= len(soldiers):
            game.soldier_detail_idx = None
            return

        soldier = soldiers[soldier_idx]
        y = start_y

        # Кнопка "Назад"
        back_rect = pygame.Rect(panel_x + 5, y, config.PANEL_WIDTH - 10, 24)
        mx, my = pygame.mouse.get_pos()
        hover_back = back_rect.collidepoint(mx, my)
        bg_back = (80, 80, 60) if hover_back else (60, 60, 50)
        pygame.draw.rect(self.r.screen, bg_back, back_rect, border_radius=3)
        pygame.draw.rect(self.r.screen, (120, 120, 80), back_rect, 1, border_radius=3)
        back_text = self.r.font_small.render("<< Назад к списку", True, (200, 200, 100))
        self.r.screen.blit(back_text, (panel_x + 10, y + 4))
        self.r.soldier_detail_rects.append(("back", back_rect))
        y += 30

        # Имя
        name_surf = self.r.font_big.render(soldier.full_name, True, (255, 255, 255))
        self.r.screen.blit(name_surf, (panel_x + 10, y))
        y += 25

        # Пол
        gender_text = "Мужчина" if soldier.gender == "male" else "Женщина"
        gender_color = (100, 150, 255) if soldier.gender == "male" else (255, 130, 180)
        gender_surf = self.r.font_normal.render(gender_text, True, gender_color)
        self.r.screen.blit(gender_surf, (panel_x + 10, y))
        y += 20

        # Роль
        role_text = getattr(soldier, 'role', 'Солдат')
        if role_text and role_text != "Солдат":
            role_surf = self.r.font_normal.render(f"Должность: {role_text}", True, (200, 180, 120))
            self.r.screen.blit(role_surf, (panel_x + 10, y))
            y += 20

        y += 5

        # Характеристики
        stats = [
            ("Здоровье", soldier.health, 100, (50, 200, 50)),
            ("Мораль", soldier.morale, 100, (100, 150, 255)),
            ("Опыт", soldier.experience, 100, (200, 180, 50)),
            ("Боевая сила", soldier.effective_skill, 100, (200, 100, 100)),
        ]

        for label, value, max_val, color in stats:
            label_surf = self.r.font_small.render(f"{label}:", True, (180, 180, 180))
            self.r.screen.blit(label_surf, (panel_x + 10, y))

            bar_x = panel_x + 90
            bar_w = 120
            bar_h = 8
            bar_y = y + 2
            pygame.draw.rect(self.r.screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            pct = min(1.0, value / max_val) if max_val > 0 else 0
            pygame.draw.rect(self.r.screen, color, (bar_x, bar_y, int(bar_w * pct), bar_h))

            val_text = f"{value}/{max_val}"
            val_surf = self.r.font_small.render(val_text, True, color)
            self.r.screen.blit(val_surf, (bar_x + bar_w + 5, y))

            y += 18

        y += 8

        # Навыки
        skills_header = self.r.font_normal.render("Навыки:", True, (200, 200, 100))
        self.r.screen.blit(skills_header, (panel_x + 10, y))
        y += 18

        skill_icons = {
            "Стрельба": "\u2694",
            "Тактика": "\u2699",
            "Выносливость": "\u26A1",
            "Маскировка": "\u2602",
            "Медицина": "\u2695",
            "Инженерное дело": "\u2692",
            "Радиосвязь": "\u260E",
            "Вождение": "\u2699",
            "Лидерство": "\u2605",
            "Навигация": "\u2690",
        }

        for skill in soldier.skills:
            icon = skill_icons.get(skill, "\u25CF")
            skill_color = (150, 200, 255) if skill in ["Стрельба", "Тактика", "Лидерство"] else (150, 220, 180)
            skill_surf = self.r.font_small.render(f" {icon} {skill}", True, skill_color)
            self.r.screen.blit(skill_surf, (panel_x + 10, y))
            y += 14

        y += 10

        # Кнопка "Вывести как отдельный юнит"
        transfer_rect = pygame.Rect(panel_x + 5, y, config.PANEL_WIDTH - 10, 28)
        mx, my = pygame.mouse.get_pos()
        hover_transfer = transfer_rect.collidepoint(mx, my)
        bg_transfer = (60, 100, 60) if hover_transfer else (40, 70, 40)
        pygame.draw.rect(self.r.screen, bg_transfer, transfer_rect, border_radius=3)
        pygame.draw.rect(self.r.screen, (100, 180, 100), transfer_rect, 1, border_radius=3)
        transfer_text = self.r.font_normal.render("Вывести как отдельный юнит", True, (150, 255, 150))
        self.r.screen.blit(transfer_text, (panel_x + 15, y + 5))
        self.r.soldier_detail_rects.append(("transfer", transfer_rect))
        y += 35

        # Кнопка "Перевести в отряд"
        t2u_rect = pygame.Rect(panel_x + 5, y, config.PANEL_WIDTH - 10, 28)
        hover_t2u = t2u_rect.collidepoint(mx, my)
        bg_t2u = (50, 80, 110) if hover_t2u else (35, 55, 75)
        pygame.draw.rect(self.r.screen, bg_t2u, t2u_rect, border_radius=3)
        pygame.draw.rect(self.r.screen, (100, 160, 220), t2u_rect, 1, border_radius=3)
        t2u_text = self.r.font_normal.render("Перевести в отряд", True, (140, 200, 255))
        self.r.screen.blit(t2u_text, (panel_x + 15, y + 5))
        self.r.soldier_detail_rects.append(("transfer_to_unit", t2u_rect))
        y += 35

        # Кнопка "Погрузить в грузовик"
        src_cell = game.map.get_cell(unit.x, unit.y)
        has_truck = False
        if src_cell:
            for u in src_cell.units:
                if isinstance(u, SupplyTruck) and u.is_alive and u.faction == unit.faction and len(u.alive_soldiers) < u.max_soldiers:
                    has_truck = True
                    break
        if has_truck:
            truck_rect = pygame.Rect(panel_x + 5, y, config.PANEL_WIDTH - 10, 28)
            hover_truck = truck_rect.collidepoint(mx, my)
            bg_truck = (100, 80, 40) if hover_truck else (70, 55, 30)
            pygame.draw.rect(self.r.screen, bg_truck, truck_rect, border_radius=3)
            pygame.draw.rect(self.r.screen, (200, 160, 60), truck_rect, 1, border_radius=3)
            truck_text = self.r.font_normal.render("Погрузить в грузовик", True, (255, 220, 100))
            self.r.screen.blit(truck_text, (panel_x + 15, y + 5))
            self.r.soldier_detail_rects.append(("load_truck", truck_rect))
            y += 35

        # Кнопка "Отправить в резерв"
        on_warehouse = False
        if src_cell:
            for u in src_cell.units:
                if isinstance(u, Warehouse) and u.faction == unit.faction and u.is_alive:
                    on_warehouse = True
                    break
        if on_warehouse:
            reserve_rect = pygame.Rect(panel_x + 5, y, config.PANEL_WIDTH - 10, 28)
            hover_reserve = reserve_rect.collidepoint(mx, my)
            bg_reserve = (80, 60, 100) if hover_reserve else (55, 40, 70)
            pygame.draw.rect(self.r.screen, bg_reserve, reserve_rect, border_radius=3)
            pygame.draw.rect(self.r.screen, (160, 120, 200), reserve_rect, 1, border_radius=3)
            reserve_text = self.r.font_normal.render("Отправить в резерв", True, (200, 170, 255))
            self.r.screen.blit(reserve_text, (panel_x + 15, y + 5))
            self.r.soldier_detail_rects.append(("send_reserve", reserve_rect))
            y += 35

    def _draw_bottom_bar(self, game):
        bar = pygame.Rect(0, config.SCREEN_HEIGHT - 32,
                          config.SCREEN_WIDTH - config.PANEL_WIDTH, 32)
        pygame.draw.rect(self.r.screen, (20, 20, 30), bar)
        pygame.draw.line(self.r.screen, (60, 60, 60),
                         (0, config.SCREEN_HEIGHT - 32),
                         (config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT - 32), 1)

        msg = self.r.font_normal.render(game.message, True, (220, 220, 220))
        self.r.screen.blit(msg, (10, config.SCREEN_HEIGHT - 26))

        # ESP status indicator
        if hasattr(game, 'ui') and game.ui and hasattr(game.ui, 'esp_menu'):
            esp = game.ui.esp_menu
            active_features = []
            if esp.show_all_enemies:
                active_features.append("ВРАГИ")
            if esp.show_enemy_stats:
                active_features.append("СТАТЫ")
            if esp.show_friendly_hp:
                active_features.append("HP")
            if esp.show_resources:
                active_features.append("РЕСУРСЫ")
            if esp.show_attack_ranges:
                active_features.append("АТАКА")
            if esp.show_unit_names:
                active_features.append("ИМЕНА")
            if esp.show_detection_range:
                active_features.append("ОБЗОР")
            
            if active_features:
                esp_text = f"ESP: {', '.join(active_features)}"
                esp_surf = self.r.font_small.render(esp_text, True, (100, 200, 255))
                self.r.screen.blit(esp_surf, (10, config.SCREEN_HEIGHT - 46))

    def _draw_zoom_indicator(self):
        text = f"Zoom: {self.r.zoom:.1f}x"
        surf = self.r.font_small.render(text, True, (200, 200, 200), (30, 30, 40))
        self.r.screen.blit(surf, (config.SCREEN_WIDTH - config.PANEL_WIDTH - 85,
                                config.SCREEN_HEIGHT - 56))

    def _draw_hourglass_button(self, game, panel_x, y):
        """Отрисовка кнопки песочных часов"""
        # Размеры кнопки
        btn_width = config.PANEL_WIDTH - 20
        btn_height = 50
        btn_x = panel_x + 10
        btn_y = y
        
        # Сохраняем rect для обработки кликов
        self.r.hourglass_rect = pygame.Rect(btn_x, btn_y, btn_width, btn_height)
        
        # Определяем состояние
        is_planning = game.phase == config.PHASE_PLANNING
        
        # Проверяем наведение мыши
        mx, my = pygame.mouse.get_pos()
        is_hovered = self.r.hourglass_rect.collidepoint(mx, my)
        
        # Цвет фона кнопки
        if is_planning:
            if is_hovered:
                bg_color = (80, 130, 80)
                border_color = (120, 230, 120)
            else:
                bg_color = (60, 100, 60)
                border_color = (100, 200, 100)
            text_color = (150, 255, 150)
        else:
            if is_hovered:
                bg_color = (130, 80, 80)
                border_color = (230, 120, 120)
            else:
                bg_color = (100, 60, 60)
                border_color = (200, 100, 100)
            text_color = (255, 150, 150)
        
        # Рисуем фон кнопки
        pygame.draw.rect(self.r.screen, bg_color, self.r.hourglass_rect, border_radius=5)
        pygame.draw.rect(self.r.screen, border_color, self.r.hourglass_rect, 2, border_radius=5)
        
        # Рисуем песочные часы
        cx = btn_x + btn_width // 2
        cy = btn_y + btn_height // 2
        
        # Верхний треугольник (стекло)
        glass_color = (180, 160, 100) if is_planning else (180, 120, 80)
        top_points = [
            (cx - 15, cy - 18),
            (cx + 15, cy - 18),
            (cx, cy - 2),
        ]
        pygame.draw.polygon(self.r.screen, glass_color, top_points)
        pygame.draw.polygon(self.r.screen, (100, 90, 60), top_points, 1)
        
        # Нижний треугольник (стекло)
        bottom_points = [
            (cx - 15, cy + 18),
            (cx + 15, cy + 18),
            (cx, cy + 2),
        ]
        pygame.draw.polygon(self.r.screen, glass_color, bottom_points)
        pygame.draw.polygon(self.r.screen, (100, 90, 60), bottom_points, 1)
        
        # Песок (верхняя часть - убывает)
        sand_color = (220, 200, 100)
        if is_planning:
            # Песок в верхнем стекле (убывает)
            sand_height = 12
            sand_points = [
                (cx - 10, cy - 18),
                (cx + 10, cy - 18),
                (cx, cy - 18 + sand_height),
            ]
            pygame.draw.polygon(self.r.screen, sand_color, sand_points)
        else:
            # Песок в нижнем стекле (накапливается)
            sand_height = 12
            sand_points = [
                (cx - 10, cy + 18),
                (cx + 10, cy + 18),
                (cx, cy + 18 - sand_height),
            ]
            pygame.draw.polygon(self.r.screen, sand_color, sand_points)
        
        # Рамка стекла
        pygame.draw.line(self.r.screen, (120, 100, 60), (cx - 15, cy - 18), (cx + 15, cy - 18), 2)
        pygame.draw.line(self.r.screen, (120, 100, 60), (cx - 15, cy + 18), (cx + 15, cy + 18), 2)
        
        # Перемычка
        pygame.draw.line(self.r.screen, (120, 100, 60), (cx - 3, cy - 2), (cx - 3, cy + 2), 2)
        pygame.draw.line(self.r.screen, (120, 100, 60), (cx + 3, cy - 2), (cx + 3, cy + 2), 2)
        
        # Текст
        if is_planning:
            label = "ЗАВЕРШИТЬ ХОД"
        else:
            label = "ХОД ПРОТИВНИКА..."
        
        text_surf = self.r.font_small.render(label, True, text_color)
        text_rect = text_surf.get_rect(center=(cx, cy + btn_height // 2 + 18))
        self.r.screen.blit(text_surf, text_rect)
