import pygame
from .. import config
from ..units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, FPVOperator, FPVDrone, ReconOperator, SupplyCache, Artillery, SoldierUnit, RadarEW


class UnitRenderer:
    def __init__(self, renderer):
        self.r = renderer

    def _is_enemy_detected(self, game, unit):
        # Если включен чит reveal, показываем всех врагов
        if hasattr(game, 'reveal_all_enemies') and game.reveal_all_enemies:
            return True
        
        cell = game.map.get_cell(unit.x, unit.y)
        if not cell or not cell.visible:
            return False
        
        # Determine observer faction based on current player
        current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
        observers = game.player_units if current_faction == config.PLAYER else game.enemy_units
        
        for observer in observers:
            if not observer.is_alive:
                continue
            dist = abs(observer.x - unit.x) + abs(observer.y - unit.y)
            # Adjacent enemies are always detected
            if dist <= 1:
                return True
            if not game.map._has_los(observer.x, observer.y, unit.x, unit.y):
                continue
            stealth = game.map._get_stealth(unit, game.map) + game.map._cell_stealth_bonus(cell.terrain)
            # Stationary observer bonus: +1 per 3 stationary turns
            stationary_bonus = observer.stationary_turns // 3 if hasattr(observer, 'stationary_turns') else 0
            # Warehouse detection penalty: trucks nearby reduce stealth
            if isinstance(unit, Warehouse):
                for dx, dy in config.DIRECTIONS:
                    adj_cell = game.map.get_cell(unit.x + dx, unit.y + dy)
                    if adj_cell:
                        for u in adj_cell.units:
                            if isinstance(u, SupplyTruck) and u.is_alive:
                                stealth -= 1
                                break
            detect_range = max(0, observer.vision_range - stealth + stationary_bonus)
            if dist <= detect_range:
                return True
        return False

    def _draw_units(self, game):
        # Рисуем мёртвую технику (серые силуэты)
        current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
        enemy_faction = config.ENEMY if current_faction == config.PLAYER else config.PLAYER
        for unit in game.dead_units:
            cell = game.map.get_cell(unit.x, unit.y)
            if not cell:
                continue
            if unit.faction == enemy_faction and not cell.visible:
                continue
            px = unit.x * self.r.tsize + self.r.camera_x
            py = unit.y * self.r.tsize + self.r.camera_y
            self._draw_dead_unit(px, py, unit)

        for unit in game.all_units:
            if not unit.is_alive:
                continue
            
            # Determine current player faction
            current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
            enemy_faction = config.ENEMY if current_faction == config.PLAYER else config.PLAYER

            # Skip enemy units that are not visible or detected
            if unit.faction == enemy_faction:
                cell = game.map.get_cell(unit.x, unit.y)
                if not cell or not cell.visible:
                    continue
                if not self._is_enemy_detected(game, unit):
                    continue
            
            # Если юнит анимируется — рисуем на позиции анимации
            if hasattr(unit, '_anim_x') and hasattr(unit, '_anim_y'):
                px = unit._anim_x * self.r.tsize + self.r.camera_x
                py = unit._anim_y * self.r.tsize + self.r.camera_y
            else:
                px = unit.x * self.r.tsize + self.r.camera_x
                py = unit.y * self.r.tsize + self.r.camera_y

            if isinstance(unit, Warehouse):
                self._draw_warehouse(px, py, unit, game)
            elif isinstance(unit, Infantry):
                self._draw_infantry(px, py, unit, game)
            elif isinstance(unit, Tank):
                self._draw_tank(px, py, unit, game)
            elif isinstance(unit, Artillery):
                self._draw_artillery(px, py, unit, game)
            elif isinstance(unit, ReconDrone):
                self._draw_drone(px, py, unit, game)
            elif isinstance(unit, SupplyTruck):
                self._draw_truck(px, py, unit, game)
            elif isinstance(unit, ReconOperator):
                self._draw_recon_operator(px, py, unit, game)
            elif isinstance(unit, FPVOperator):
                self._draw_fpv_operator(px, py, unit, game)
            elif isinstance(unit, FPVDrone):
                self._draw_fpv_in_flight(px, py, unit, game)
            elif isinstance(unit, SupplyCache):
                self._draw_supply_cache(px, py, unit, game)
            elif isinstance(unit, SoldierUnit):
                self._draw_soldier_unit(px, py, unit, game)
            elif isinstance(unit, RadarEW):
                self._draw_radar_ew(px, py, unit, game)

            # Кружок состояния юнита (слева снизу)
            self._draw_unit_status_circle(px, py, unit, game)

            # Индикатор еды (справа снизу)
            self._draw_food_indicator(px, py, unit, game)

            if hasattr(unit, 'is_understaffed') and unit.is_understaffed:
                self._draw_understaffed_indicator(px, py, unit)

    def _draw_unit_status_circle(self, px, py, unit, game):
        """Рисует кружок состояния юнита слева снизу"""
        ts = self.r.tsize
        # Позиция — левый нижний угол клетки
        cx = px + max(5, ts // 6)
        cy = py + ts - max(5, ts // 6)
        r = max(4, ts // 7)
        
        # Определяем цвет по состоянию
        can_move = not unit.moved
        has_attack = hasattr(unit, 'attacked') and not unit.attacked
        has_ammo = True
        if hasattr(unit, 'ammo'):
            has_ammo = unit.ammo > 0
        elif hasattr(unit, 'alive_soldiers'):
            has_ammo = any(s.ammo > 0 for s in unit.alive_soldiers)
        
        if isinstance(unit, (Warehouse, SupplyCache)):
            # Склады/погреба — серый
            color = (120, 120, 120)
        elif can_move and has_attack and has_ammo:
            # Зелёный — всё доступно
            color = (50, 220, 50)
        elif can_move:
            # Жёлтый — только движение
            color = (220, 220, 50)
        elif has_attack and has_ammo:
            # Оранжевый — только атака
            color = (220, 150, 30)
        else:
            # Красный — всё использовано
            color = (180, 50, 50)
        
        # Рисуем кружок
        pygame.draw.circle(self.r.screen, color, (cx, cy), r)
        pygame.draw.circle(self.r.screen, (0, 0, 0), (cx, cy), r, 1)
        
        # Белый блик сверху
        highlight_r = max(2, r // 2)
        pygame.draw.circle(self.r.screen, (255, 255, 255, 80), (cx - 1, cy - 1), highlight_r)

    def _get_food_pct(self, unit):
        if isinstance(unit, Warehouse) or isinstance(unit, SupplyCache):
            return None
        if isinstance(unit, ReconDrone):
            return None
        if isinstance(unit, SoldierUnit):
            s = unit.soldier
            return s.food / s.max_food if s.max_food > 0 else 1.0
        if hasattr(unit, 'alive_soldiers') and unit.alive_soldiers:
            total_food = sum(s.food for s in unit.alive_soldiers)
            total_max = sum(s.max_food for s in unit.alive_soldiers)
            return total_food / total_max if total_max > 0 else 1.0
        return None

    def _draw_food_indicator(self, px, py, unit, game):
        ts = self.r.tsize
        pct = self._get_food_pct(unit)
        if pct is None:
            return

        cx = px + ts - max(5, ts // 6)
        cy = py + ts - max(5, ts // 6)

        if pct > 0.3:
            color = (50, 200, 50)
            dark = (30, 140, 30)
        elif pct > 0:
            color = (220, 200, 50)
            dark = (160, 140, 30)
        else:
            color = (220, 50, 50)
            dark = (160, 30, 30)

        w = max(6, ts // 4)
        h = max(8, ts // 3)
        bone_w = max(1, ts // 14)
        bone_len = max(2, ts // 10)
        pad = max(4, ts // 6)
        surf_w = w + bone_len + pad * 2
        surf_h = h + bone_len + pad * 2
        surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        scx = surf_w // 2
        scy = surf_h // 2

        body_rect = pygame.Rect(scx - w // 2, scy - h // 2 + 1, w, h - 2)
        pygame.draw.ellipse(surf, color, body_rect)
        pygame.draw.ellipse(surf, dark, body_rect, 1)

        pygame.draw.line(surf, (220, 210, 180),
                         (scx, scy - h // 2 + 1),
                         (scx, scy - h // 2 - bone_len), bone_w)
        pygame.draw.circle(surf, (240, 230, 200),
                           (scx, scy - h // 2 - bone_len), max(1, bone_w - 1))

        rotated = pygame.transform.rotate(surf, 45)
        rw, rh = rotated.get_size()
        self.r.screen.blit(rotated, (cx - rw // 2, cy - rh // 2))

    def _draw_understaffed_indicator(self, px, py, unit):
        ts = self.r.tsize
        cx = px + ts - 2
        cy = py + 2
        r = max(4, ts // 6)
        pygame.draw.circle(self.r.screen, (160, 160, 160), (cx, cy), r)
        pygame.draw.circle(self.r.screen, (80, 80, 80), (cx, cy), r, 1)
        font = pygame.font.SysFont("consolas", max(8, ts // 3))
        mark = font.render("!", True, (80, 80, 80))
        mr = mark.get_rect(center=(cx, cy))
        self.r.screen.blit(mark, mr)

    def _draw_dead_unit(self, px, py, unit):
        ts = self.r.tsize
        gray = (70, 70, 70)
        dark = (40, 40, 40)
        cx, cy = px + ts // 2, py + ts // 2
        if isinstance(unit, (Warehouse, SupplyCache)):
            bw = ts * 3 // 4
            bh = ts // 2
            pygame.draw.rect(self.r.screen, gray,
                             (px + (ts - bw) // 2, py + ts // 3, bw, bh))
            pygame.draw.rect(self.r.screen, dark,
                             (px + (ts - bw) // 2, py + ts // 3, bw, bh), 1)
        elif isinstance(unit, Tank):
            track_h = max(3, ts // 6)
            track_y = py + ts - track_h - 2
            track_rect = pygame.Rect(px + 3, track_y, ts - 6, track_h)
            pygame.draw.rect(self.r.screen, dark, track_rect)
            pygame.draw.rect(self.r.screen, (30, 30, 30), track_rect, 1)
            body_y = track_y - ts // 4
            body = pygame.Rect(px + 5, body_y, ts - 10, ts // 4)
            pygame.draw.rect(self.r.screen, gray, body)
            pygame.draw.rect(self.r.screen, dark, body, 1)
            turret_w = ts // 2
            turret_h = ts // 4
            turret = pygame.Rect(px + (ts - turret_w) // 2, body_y - turret_h + 2, turret_w, turret_h)
            pygame.draw.ellipse(self.r.screen, gray, turret)
            pygame.draw.ellipse(self.r.screen, dark, turret, 1)
            barrel_x = px + ts // 2 + turret_w // 4
            barrel_y = body_y - turret_h // 2
            barrel = pygame.Rect(barrel_x, barrel_y, ts // 3, max(2, ts // 14))
            pygame.draw.rect(self.r.screen, (50, 50, 50), barrel)
            pygame.draw.rect(self.r.screen, dark, barrel, 1)
        elif isinstance(unit, SupplyTruck):
            cab_w = ts // 4
            cab_h = ts // 3
            cargo_w = ts // 2
            cargo_h = ts * 2 // 5
            pygame.draw.rect(self.r.screen, gray,
                             (px + 2, py + ts - cab_h - 4, cab_w, cab_h))
            pygame.draw.rect(self.r.screen, gray,
                             (px + cab_w, py + ts - cargo_h - 4, cargo_w, cargo_h))
            pygame.draw.rect(self.r.screen, dark,
                             (px + 2, py + ts - cab_h - 4, cab_w, cab_h), 1)
            pygame.draw.rect(self.r.screen, dark,
                             (px + cab_w, py + ts - cargo_h - 4, cargo_w, cargo_h), 1)
        elif isinstance(unit, Artillery):
            track_h = max(3, ts // 6)
            track_y = py + ts - track_h - 2
            track_rect = pygame.Rect(px + 3, track_y, ts - 6, track_h)
            pygame.draw.rect(self.r.screen, dark, track_rect)
            pygame.draw.rect(self.r.screen, (30, 30, 30), track_rect, 1)
            body_y = track_y - ts // 4
            body = pygame.Rect(px + 5, body_y, ts - 10, ts // 4)
            pygame.draw.rect(self.r.screen, gray, body)
            pygame.draw.rect(self.r.screen, dark, body, 1)
            barrel_x = px + ts // 2
            barrel_y = body_y - ts // 6
            barrel = pygame.Rect(barrel_x, barrel_y, ts // 2, max(2, ts // 14))
            pygame.draw.rect(self.r.screen, (50, 50, 50), barrel)
            pygame.draw.rect(self.r.screen, dark, barrel, 1)
        else:
            r = max(3, ts // 5)
            pygame.draw.circle(self.r.screen, gray, (cx, cy), r)
            pygame.draw.circle(self.r.screen, dark, (cx, cy), r, 1)
        cross_s = max(3, ts // 5)
        pygame.draw.line(self.r.screen, (180, 50, 50),
                         (cx - cross_s, cy - cross_s), (cx + cross_s, cy + cross_s), max(1, ts // 12))
        pygame.draw.line(self.r.screen, (180, 50, 50),
                         (cx + cross_s, cy - cross_s), (cx - cross_s, cy + cross_s), max(1, ts // 12))

    def _draw_soldier_unit(self, px, py, unit, game):
        import math
        ts = self.r.tsize
        color = unit.color
        cx, cy = px + ts // 2, py + ts // 2
        r = max(2, ts // 4)

        is_selected = game.selected_unit is unit
        if is_selected:
            pygame.draw.circle(self.r.screen, (255, 255, 100), (cx, cy), r + 2, 2)

        pygame.draw.circle(self.r.screen, color, (cx, cy), r)
        pygame.draw.circle(self.r.screen, (255, 255, 255), (cx, cy), r, 1)

        angle = unit.direction_angle
        if angle is not None:
            arrow_len = r + 3
            ax = cx + int(math.cos(angle) * arrow_len)
            ay = cy + int(math.sin(angle) * arrow_len)
            pygame.draw.line(self.r.screen, (255, 255, 0), (cx, cy), (ax, ay), 1)
            head_len = 3
            for da in [0.4, -0.4]:
                hx = ax + int(math.cos(angle + da) * head_len)
                hy = ay + int(math.sin(angle + da) * head_len)
                pygame.draw.line(self.r.screen, (255, 255, 0), (ax, ay), (hx, hy), 1)

        name_short = unit.soldier.short_name if len(unit.soldier.short_name) <= 8 else unit.soldier.short_name[:7] + "."
        nsurf = self.r.font_small.render(name_short, True, (255, 255, 255))
        self.r.screen.blit(nsurf, (cx - nsurf.get_width() // 2, py + ts - 2))

    def _draw_supply_cache(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        rect = pygame.Rect(px + 2, py + 2, ts - 4, ts - 4)
        
        # Blue cross indicator if this cache is a route target for selected truck
        is_route_target = False
        if game.dest_select_mode:
            is_route_target = True
        elif game.selected_unit and isinstance(game.selected_unit, SupplyTruck):
            route = game.selected_unit.supply_route
            if route and route["dest"] is unit:
                is_route_target = True
        
        if unit.build_turns < unit.build_required:
            # Under construction - show dashed outline and progress
            pygame.draw.rect(self.r.screen, (100, 80, 40), rect, border_radius=3)
            # Dashed border
            dash_len = max(2, ts // 8)
            for i in range(0, ts - 4, dash_len * 2):
                # Top
                pygame.draw.line(self.r.screen, (200, 180, 100), 
                               (px + 2 + i, py + 2), 
                               (px + 2 + min(i + dash_len, ts - 4), py + 2), 2)
                # Bottom
                pygame.draw.line(self.r.screen, (200, 180, 100), 
                               (px + 2 + i, py + ts - 2), 
                               (px + 2 + min(i + dash_len, ts - 4), py + ts - 2), 2)
            for i in range(0, ts - 4, dash_len * 2):
                # Left
                pygame.draw.line(self.r.screen, (200, 180, 100), 
                               (px + 2, py + 2 + i), 
                               (px + 2, py + 2 + min(i + dash_len, ts - 4)), 2)
                # Right
                pygame.draw.line(self.r.screen, (200, 180, 100), 
                               (px + ts - 2, py + 2 + i), 
                               (px + ts - 2, py + 2 + min(i + dash_len, ts - 4)), 2)
            # Construction symbol
            if ts >= 20:
                font = pygame.font.SysFont(None, 18)
                label = font.render("🔨", True, (255, 255, 200))
                self.r.screen.blit(label, (px + ts // 2 - label.get_width() // 2, py + 2))
            # Progress bar
            progress = unit.build_turns / unit.build_required
            bar_w = ts - 8
            pygame.draw.rect(self.r.screen, (80, 80, 80), (px + 4, py + ts - 6, bar_w, 4))
            pygame.draw.rect(self.r.screen, (255, 200, 0), (px + 4, py + ts - 6, int(bar_w * progress), 4))
        else:
            # Completed - normal appearance
            pygame.draw.rect(self.r.screen, color, rect, border_radius=3)
            pygame.draw.rect(self.r.screen, (200, 200, 200), rect, 2, border_radius=3)
            font = pygame.font.SysFont(None, 20)
            label = font.render("П", True, (255, 255, 200))
            self.r.screen.blit(label, (px + ts // 2 - label.get_width() // 2, py + ts // 2 - label.get_height() // 2))
            # Blue cross indicator for route target
            if is_route_target:
                cross_size = max(4, ts // 4)
                cx, cy = px + ts // 2, py + ts // 2
                pygame.draw.line(self.r.screen, (0, 150, 255),
                               (cx - cross_size, cy), (cx + cross_size, cy), 2)
                pygame.draw.line(self.r.screen, (0, 150, 255),
                               (cx, cy - cross_size), (cx, cy + cross_size), 2)

    def _draw_infantry(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        count = unit.soldiers
        if ts >= 16:
            cols = max(2, int(count ** 0.5 + 0.5))
            rows = (count + cols - 1) // cols
            w = max(2, ts // (cols + 2))
            h = max(3, ts // (rows + 2))
            gap_x = max(1, w // 4)
            gap_y = max(1, h // 4)
            block_w = cols * w + (cols - 1) * gap_x
            block_h = rows * h + (rows - 1) * gap_y
            start_x = px + (ts - block_w) // 2 + w // 2
            start_y = py + (ts - block_h) // 2 + h // 2

            positions = []
            for row in range(rows):
                for col in range(cols):
                    if len(positions) >= count:
                        break
                    x = start_x + col * (w + gap_x)
                    y = start_y + row * (h + gap_y)
                    positions.append((int(x), int(y)))
            
            # Рисуем солдат с учетом ранений
            alive_soldiers = unit.alive_soldiers
            for i in range(min(count, len(positions))):
                cx, cy = positions[i]
                
                # Определяем цвет на основе ранения
                if i < len(alive_soldiers):
                    soldier = alive_soldiers[i]
                    if soldier.wound_level == 0:  # Здоров
                        soldier_color = color
                    elif soldier.wound_level == 1:  # Лёгкое ранение
                        soldier_color = (255, 255, 100)  # Жёлтый
                    elif soldier.wound_level == 2:  # Среднее ранение
                        soldier_color = (255, 165, 0)  # Оранжевый
                    else:  # Тяжёлое ранение
                        soldier_color = (255, 50, 50)  # Красный
                else:
                    soldier_color = color
                
                pygame.draw.rect(self.r.screen, soldier_color, (cx - w//2, cy - h//2, w, h))
                pygame.draw.rect(self.r.screen, (0, 0, 0), (cx - w//2, cy - h//2, w, h), 1)
                
                # Индикатор ранения (маленький крестик)
                if i < len(alive_soldiers) and alive_soldiers[i].wound_level >= 2:
                    pygame.draw.line(self.r.screen, (255, 255, 255),
                                   (cx - 1, cy - 1),
                                   (cx + 1, cy + 1), 1)
                    pygame.draw.line(self.r.screen, (255, 255, 255),
                                   (cx + 1, cy - 1),
                                   (cx - 1, cy + 1), 1)

        if ts >= 20:
            label = self.r.font_small.render(str(unit.soldiers), True, (255, 255, 255))
            self.r.screen.blit(label, (px + 2, py + 1))

    def _draw_tank(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        # Гусеница (одна полоса внизу)
        track_h = max(3, ts // 6)
        track_y = py + ts - track_h - 2
        track_rect = pygame.Rect(px + 3, track_y, ts - 6, track_h)
        pygame.draw.rect(self.r.screen, (50, 50, 50), track_rect)
        pygame.draw.rect(self.r.screen, (0, 0, 0), track_rect, 1)

        # Рифление на гусенице
        seg_w = max(3, ts // 8)
        for i in range(0, ts - 6, seg_w * 2):
            pygame.draw.line(self.r.screen, (70, 70, 70),
                           (px + 3 + i, track_y), (px + 3 + i, track_y + track_h), 1)

        # Корпус
        body_y = track_y - ts // 4
        body = pygame.Rect(px + 5, body_y, ts - 10, ts // 4)
        pygame.draw.rect(self.r.screen, color, body)
        pygame.draw.rect(self.r.screen, (0, 0, 0), body, 1)

        # Башня (овал)
        turret_w = ts // 2
        turret_h = ts // 4
        turret = pygame.Rect(px + (ts - turret_w) // 2, body_y - turret_h + 2, turret_w, turret_h)
        pygame.draw.ellipse(self.r.screen, color, turret)
        pygame.draw.ellipse(self.r.screen, (0, 0, 0), turret, 1)

        # Ствол пушки
        barrel_x = px + ts // 2 + turret_w // 4
        barrel_y = body_y - turret_h // 2
        barrel = pygame.Rect(barrel_x, barrel_y, ts // 3, max(2, ts // 14))
        pygame.draw.rect(self.r.screen, (90, 90, 90), barrel)
        pygame.draw.rect(self.r.screen, (0, 0, 0), barrel, 1)

        bar_w = max(16, ts - 4)
        if hasattr(unit, 'fuel') and hasattr(unit, 'max_fuel') and unit.max_fuel > 0:
            self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                           unit.fuel / unit.max_fuel, (220, 180, 50))

    def _draw_artillery(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        # Основание артиллерии
        base = pygame.Rect(px + ts // 6, py + ts // 2, ts * 2 // 3, ts // 3)
        pygame.draw.rect(self.r.screen, color, base)
        pygame.draw.rect(self.r.screen, (0, 0, 0), base, 1)

        # Ствол (длинный и тонкий)
        barrel = pygame.Rect(px + ts // 3, py + ts // 6, ts // 3, ts // 2)
        pygame.draw.rect(self.r.screen, (100, 100, 100), barrel)
        pygame.draw.rect(self.r.screen, (0, 0, 0), barrel, 1)

        # Колеса
        wheel_r = max(2, ts // 10)
        pygame.draw.circle(self.r.screen, (80, 80, 80), (px + ts // 3, py + ts * 2 // 3), wheel_r)
        pygame.draw.circle(self.r.screen, (80, 80, 80), (px + ts * 2 // 3, py + ts * 2 // 3), wheel_r)

        bar_w = max(16, ts - 4)
        self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                       unit.ammo / unit.max_ammo, (200, 80, 80))

    def _draw_radar_ew(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        # Рисуем радиус действия РЭБ если юнит выбран
        if selected:
            center_x = px + ts // 2
            center_y = py + ts // 2
            radius_px = int(unit.jam_range * ts)
            
            # Создаем полупрозрачную поверхность
            surf = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 50, 50, 30), (radius_px, radius_px), radius_px)
            pygame.draw.circle(surf, (200, 50, 50, 60), (radius_px, radius_px), radius_px, 2)
            self.r.screen.blit(surf, (center_x - radius_px, center_y - radius_px))

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        # Основание (машина)
        body = pygame.Rect(px + ts // 6, py + ts // 2, ts * 2 // 3, ts // 3)
        pygame.draw.rect(self.r.screen, color, body)
        pygame.draw.rect(self.r.screen, (0, 0, 0), body, 1)

        # Антенна радара (большая тарелка)
        cx = px + ts // 2
        cy = py + ts // 3
        r = ts // 4
        pygame.draw.circle(self.r.screen, (150, 150, 150), (cx, cy), r)
        pygame.draw.circle(self.r.screen, (0, 0, 0), (cx, cy), r, 1)
        # Внутренний круг
        pygame.draw.circle(self.r.screen, (100, 200, 200), (cx, cy), r // 2)

        # Стойка антенны
        pygame.draw.line(self.r.screen, (100, 100, 100), (cx, cy + r),
                         (cx, py + ts // 2), max(1, ts // 16))

        # Индикатор РЭБ (мигающий круг)
        if unit.is_jammer:
            import math
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 0.5 + 0.5
            jam_color = (int(200 * pulse), int(50 * pulse), int(50 * pulse))
            pygame.draw.circle(self.r.screen, jam_color, (px + ts - 4, py + 4), max(2, ts // 10))

        bar_w = max(16, ts - 4)
        self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                       unit.fuel / unit.max_fuel, (220, 180, 50))

    def _draw_drone(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        off = ts // 6
        inner = ts // 3
        w = max(2, ts // 16)
        pygame.draw.line(self.r.screen, color, (px + off, py + off),
                         (px + ts - off, py + ts - off), w)
        pygame.draw.line(self.r.screen, color, (px + ts - off, py + off),
                         (px + off, py + ts - off), w)
        center = (px + ts // 2, py + ts // 2)
        pygame.draw.circle(self.r.screen, (200, 200, 255), center, max(3, ts // 8))
        pygame.draw.circle(self.r.screen, color, center, max(3, ts // 8), 1)

        bar_w = max(16, ts - 4)
        self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                       unit.battery / unit.max_battery, (50, 150, 255))

    def _draw_fpv_operator(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        # Antenna dish
        cx, cy = px + ts // 2, py + ts // 3
        r = ts // 4
        pygame.draw.circle(self.r.screen, (80, 80, 100), (cx, cy), r)
        pygame.draw.circle(self.r.screen, (0, 0, 0), (cx, cy), r, 1)
        # Antenna line
        pygame.draw.line(self.r.screen, (150, 150, 150),
                         (cx, cy - r), (cx + r * 2, cy - r * 2), max(1, ts // 16))
        # Body/screen
        body = pygame.Rect(px + ts // 4, py + ts // 2, ts // 2, ts // 3)
        pygame.draw.rect(self.r.screen, (60, 60, 70), body)
        pygame.draw.rect(self.r.screen, (0, 0, 0), body, 1)
        # Screen glow
        screen_r = pygame.Rect(px + ts // 3, py + ts * 3 // 5, ts // 4, ts // 6)
        pygame.draw.rect(self.r.screen, (50, 200, 50), screen_r)

        # FPV stock bar
        bar_w = max(16, ts - 4)
        self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                       unit.fpv_stock / unit.max_stock, (180, 50, 180))

    def _draw_recon_operator(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)

        # Control console body
        body = pygame.Rect(px + ts // 4, py + ts // 3, ts // 2, ts // 2)
        pygame.draw.rect(self.r.screen, color, body)
        pygame.draw.rect(self.r.screen, (0, 0, 0), body, 1)
        # Screen
        screen_r = pygame.Rect(px + ts // 3, py + ts * 2 // 5, ts // 4, ts // 5)
        pygame.draw.rect(self.r.screen, (50, 150, 200), screen_r)
        # Antenna
        cx = px + ts // 2
        cy = py + ts // 4
        pygame.draw.line(self.r.screen, (150, 150, 150), (cx, cy),
                         (cx, cy + ts // 6), max(1, ts // 16))
        pygame.draw.circle(self.r.screen, (100, 200, 200), (cx, cy), max(2, ts // 12))

        # Battery bar
        bar_w = max(16, ts - 4)
        self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                       unit.batteries / unit.max_batteries, (50, 180, 200))

        # Draw line to linked drone
        if unit.drone and unit.drone.is_alive:
            drone = unit.drone
            drone_px = drone.x * ts + ts // 2 + self.r.camera_x
            drone_py = drone.y * ts + ts // 2 + self.r.camera_y
            op_cx = px + ts // 2
            op_cy = py + ts // 2
            
            line_color = (50, 200, 50) if not drone.jammed else (200, 50, 50)
            pygame.draw.line(self.r.screen, line_color, (op_cx, op_cy), 
                           (int(drone_px), int(drone_py)), max(1, ts // 16))

    def _draw_fpv_in_flight(self, px, py, unit, game):
        ts = self.r.tsize
        cx, cy = px + ts // 2, py + ts // 2
        # Flying FPV: small shape with trail line from operator
        ops = [u for u in game.all_units if isinstance(u, FPVOperator) and u.is_alive and u.faction == unit.faction]
        if ops:
            closest = min(ops, key=lambda o: abs(o.x - unit.x) + abs(o.y - unit.y))
            opx = closest.x * ts + ts // 2 + self.r.camera_x
            opy = closest.y * ts + ts // 2 + self.r.camera_y
            color = (200, 50, 200, 80) if unit.faction == config.PLAYER else (200, 100, 50, 80)
            pygame.draw.line(self.r.screen, color, (opx, opy), (cx, cy), max(1, ts // 20))

        # Drone body
        r = max(3, ts // 8)
        pygame.draw.circle(self.r.screen, (200, 50, 200), (int(cx), int(cy)), r)
        pygame.draw.circle(self.r.screen, (255, 100, 255), (int(cx), int(cy)), r, 1)
        # Wings
        w = max(2, ts // 6)
        pygame.draw.line(self.r.screen, (180, 30, 180), (int(cx - w), int(cy)), (int(cx + w), int(cy)), max(1, ts // 20))
        pygame.draw.line(self.r.screen, (180, 30, 180), (int(cx), int(cy - w)), (int(cx), int(cy + w)), max(1, ts // 20))

        # Label
        if ts >= 20:
            label = self.r.font_small.render("FPV", True, (255, 200, 255))
            self.r.screen.blit(label, (px + 2, py + 2))

        # Target indicator
        if unit.target and unit.target.is_alive:
            tx = unit.target.x * ts + ts // 2 + self.r.camera_x
            ty = unit.target.y * ts + ts // 2 + self.r.camera_y
            pygame.draw.circle(self.r.screen, (255, 50, 50), (int(tx), int(ty)), max(3, ts // 6), max(1, ts // 20))

    def _draw_truck(self, px, py, unit, game):
        ts = self.r.tsize
        color = unit.color
        selected = game.selected_unit is unit

        if selected:
            pygame.draw.rect(self.r.screen, (255, 255, 0),
                             (px - 1, py - 1, ts + 2, ts + 2), 2)
            # Purple dot indicator for selected truck
            dot_r = max(3, ts // 6)
            pygame.draw.circle(self.r.screen, (180, 0, 255),
                             (px + ts // 2, py + ts // 2), dot_r)
            pygame.draw.circle(self.r.screen, (255, 255, 255),
                             (px + ts // 2, py + ts // 2), dot_r, 1)

        cab_w = ts // 4
        cab_h = ts // 3
        cargo_w = ts // 2
        cargo_h = ts * 2 // 5
        pygame.draw.rect(self.r.screen, (80, 80, 80),
                         (px + 2, py + ts - cab_h - 4, cab_w, cab_h))
        pygame.draw.rect(self.r.screen, color,
                         (px + cab_w, py + ts - cargo_h - 4, cargo_w, cargo_h))
        pygame.draw.rect(self.r.screen, (0, 0, 0),
                         (px + 2, py + ts - cab_h - 4, cab_w, cab_h), 1)
        pygame.draw.rect(self.r.screen, (0, 0, 0),
                         (px + cab_w, py + ts - cargo_h - 4, cargo_w, cargo_h), 1)

        r = max(2, ts // 14)
        pygame.draw.circle(self.r.screen, (40, 40, 40), (px + cab_w // 2, py + ts - 4), r)
        pygame.draw.circle(self.r.screen, (40, 40, 40), (px + cab_w + cargo_w // 3, py + ts - 4), r)
        pygame.draw.circle(self.r.screen, (40, 40, 40), (px + cab_w + cargo_w * 2 // 3, py + ts - 4), r)

        bar_w = max(16, ts - 4)
        if hasattr(unit, 'fuel') and hasattr(unit, 'max_fuel') and unit.max_fuel > 0:
            self._draw_bar(px + 2, py + 2, bar_w, max(3, ts // 12),
                           unit.fuel / unit.max_fuel, (220, 180, 50))

        cargo_icons = {
            "supplies": ((50, 200, 50), "П"),
            "ammo": ((220, 50, 50), "Б"),
            "fuel": ((220, 180, 50), "Т"),
            "batteries": ((50, 180, 200), "Э"),
            "fpv_drone": ((200, 50, 200), "F"),
            "recon_drone": ((50, 200, 220), "Р"),
        }
        icon_y = py + max(5, ts // 5)
        icon_r = max(3, ts // 10)
        icon_x = px + ts // 2
        active = [(k, v) for k, v in cargo_icons.items() if unit.cargo.get(k, 0) > 0]
        if active:
            total_w = len(active) * (icon_r * 2 + 2) - 2
            start_x = icon_x - total_w // 2
            for i, (key, (color, letter)) in enumerate(active):
                cx = start_x + i * (icon_r * 2 + 2) + icon_r
                pygame.draw.circle(self.r.screen, color, (cx, icon_y), icon_r)
                pygame.draw.circle(self.r.screen, (0, 0, 0), (cx, icon_y), icon_r, 1)
                if ts >= 20:
                    fnt = pygame.font.SysFont("consolas", max(6, ts // 5))
                    surf = fnt.render(letter, True, (255, 255, 255))
                    self.r.screen.blit(surf, surf.get_rect(center=(cx, icon_y)))

    def _draw_warehouse(self, px, py, unit, game=None):
        ts = self.r.tsize
        bw = ts * 3 // 4
        bh = ts // 2
        pygame.draw.rect(self.r.screen, (100, 100, 120),
                         (px + (ts - bw) // 2, py + ts // 3, bw, bh))
        pygame.draw.rect(self.r.screen, (0, 0, 0),
                         (px + (ts - bw) // 2, py + ts // 3, bw, bh), 2)
        points = [
            (px + (ts - bw) // 2 - 2, py + ts // 3),
            (px + ts // 2, py + ts // 6),
            (px + (ts + bw) // 2 + 2, py + ts // 3),
        ]
        pygame.draw.polygon(self.r.screen, (130, 50, 50), points)
        pygame.draw.polygon(self.r.screen, (0, 0, 0), points, 2)
        door_w = ts // 5
        door_h = ts // 4
        pygame.draw.rect(self.r.screen, (60, 40, 20),
                         (px + (ts - door_w) // 2, py + ts * 2 // 3, door_w, door_h))
        # Purple dot indicator if this warehouse is origin target
        if game and game.origin_select_mode:
            dot_r = max(4, ts // 5)
            pygame.draw.circle(self.r.screen, (180, 0, 255),
                             (px + ts // 2, py + ts // 2), dot_r)
            pygame.draw.circle(self.r.screen, (255, 255, 255),
                             (px + ts // 2, py + ts // 2), dot_r, 1)

    def _draw_bar(self, x, y, w, h, pct, color):
        if pct < 0:
            pct = 0
        if pct > 1:
            pct = 1
        pygame.draw.rect(self.r.screen, (40, 40, 40), (x, y, w, h))
        if pct > 0:
            fill_w = int(w * pct)
            pygame.draw.rect(self.r.screen, color, (x, y, fill_w, h))
