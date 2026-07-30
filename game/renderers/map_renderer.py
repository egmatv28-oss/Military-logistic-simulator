import pygame
from .. import config
from ..units import Infantry, Tank, SupplyTruck, SupplyCache, Artillery


class MapRenderer:
    def __init__(self, renderer):
        self.r = renderer

    def _draw_map(self, game):
        ts = self.r.tsize
        w, h = config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT
        start_x = max(0, -self.r.camera_x // ts - 1)
        start_y = max(0, -self.r.camera_y // ts - 1)
        end_x = min(game.map.width, start_x + w // ts + 2)
        end_y = min(game.map.height, start_y + h // ts + 2)
        
        # Determine current player faction for explored check
        current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                cell = game.map.grid[y][x]
                px = x * ts + self.r.camera_x
                py = y * ts + self.r.camera_y
                rect = pygame.Rect(px, py, ts, ts)

                # Check if cell is explored for current faction
                is_explored = False
                if current_faction == config.PLAYER:
                    is_explored = cell.explored_player
                else:
                    is_explored = cell.explored_enemy
                
                # Don't draw terrain for unexplored cells
                if not is_explored:
                    pygame.draw.rect(self.r.screen, (10, 10, 15), rect)
                    continue

                if cell.terrain == config.FIELD:
                    c = (90, 150, 55) if (x + y) % 2 == 0 else (100, 160, 60)
                    pygame.draw.rect(self.r.screen, c, rect)
                elif cell.terrain == config.FOREST:
                    pygame.draw.rect(self.r.screen, (30, 90, 30), rect)
                    if ts >= 20:
                        off = ts // 6
                        r = ts // 8
                        for i in range(3):
                            ex = px + off + i * off * 2
                            ey = py + off + (i * off) % ts
                            pygame.draw.ellipse(self.r.screen, (20, 100, 20),
                                                (ex - r, ey - r, r * 2, r * 2))
                            pygame.draw.ellipse(self.r.screen, (0, 0, 0),
                                                (ex - r, ey - r, r * 2, r * 2), 1)
                elif cell.terrain == config.CITY:
                    pygame.draw.rect(self.r.screen, (120, 100, 80), rect)
                    pygame.draw.rect(self.r.screen, (90, 70, 50), rect, 1)
                    if ts >= 20:
                        bw = ts * 3 // 4
                        bh = ts // 2
                        bx = px + (ts - bw) // 2
                        by = py + ts - bh - 2
                        pygame.draw.rect(self.r.screen, (160, 140, 120), (bx, by, bw, bh))
                        pygame.draw.rect(self.r.screen, (80, 60, 40), (bx, by, bw, bh), 1)
                        roof_pts = [
                            (bx - 1, by),
                            (px + ts // 2, by - ts // 4),
                            (bx + bw + 1, by),
                        ]
                        pygame.draw.polygon(self.r.screen, (180, 60, 50), roof_pts)
                        pygame.draw.polygon(self.r.screen, (120, 40, 30), roof_pts, 1)
                        win_y = by + bh // 4
                        win_s = max(2, ts // 10)
                        for wi in range(2):
                            win_x = bx + bw // 3 + wi * bw // 3
                            pygame.draw.rect(self.r.screen, (220, 200, 100),
                                             (win_x - win_s, win_y, win_s * 2, win_s))
                elif cell.terrain == config.ROAD:
                    c = (55, 50, 45) if (x + y) % 2 == 0 else (65, 60, 55)
                    pygame.draw.rect(self.r.screen, c, rect)
                elif cell.terrain == config.RIVER:
                    pygame.draw.rect(self.r.screen, (50, 100, 200), rect)
                    if ts >= 16:
                        for wx in range(0, ts, max(4, ts // 6)):
                            wy = (wx + x * 3 + y * 5) % ts
                            wr = max(2, ts // 12)
                            pygame.draw.ellipse(self.r.screen, (60, 120, 220),
                                                (px + wx, py + wy, wr * 2, wr))

                # Отрисовка укрепления на клетке
                if cell.entrenchment > 0:
                    entrench_level = cell.entrenchment // 25
                    if entrench_level == 1:
                        pygame.draw.rect(self.r.screen, (180, 140, 60),
                                       (px + 2, py + ts - 4, ts - 4, 2))
                    elif entrench_level == 2:
                        pygame.draw.rect(self.r.screen, (200, 150, 50),
                                       (px + 2, py + ts - 6, ts - 4, 2))
                        pygame.draw.rect(self.r.screen, (200, 150, 50),
                                       (px + 2, py + ts - 3, ts - 4, 2))
                    elif entrench_level == 3:
                        pygame.draw.rect(self.r.screen, (220, 160, 40),
                                       (px + 2, py + ts - 8, ts - 4, 3))
                        for i in range(3):
                            pygame.draw.circle(self.r.screen, (220, 160, 40),
                                             (px + 4 + i * (ts // 4), py + ts - 4), 2)
                    elif entrench_level >= 4:
                        pygame.draw.rect(self.r.screen, (240, 170, 30),
                                       (px + 2, py + ts - 10, ts - 4, 4))
                        pygame.draw.line(self.r.screen, (240, 170, 30),
                                       (px + 4, py + ts - 12), (px + ts - 4, py + ts - 6), 2)
                        pygame.draw.line(self.r.screen, (240, 170, 30),
                                       (px + ts - 4, py + ts - 12), (px + 4, py + ts - 6), 2)

                # Dim explored-but-not-visible cells
                if not cell.visible:
                    dim = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    dim.fill((0, 0, 0, 120))
                    self.r.screen.blit(dim, (px, py))

                pygame.draw.rect(self.r.screen, (20, 20, 20), rect, 1)

    def _draw_fog(self, game):
        ts = self.r.tsize
        overlay = pygame.Surface((config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)
        
        # Determine current player faction for explored check
        current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
        
        for y in range(game.map.height):
            for x in range(game.map.width):
                cell = game.map.grid[y][x]
                px = x * ts + self.r.camera_x
                py = y * ts + self.r.camera_y
                rect = pygame.Rect(px, py, ts, ts)

                # Check if cell is explored for current faction
                is_explored = False
                if current_faction == config.PLAYER:
                    is_explored = cell.explored_player
                else:
                    is_explored = cell.explored_enemy

                if not is_explored:
                    pygame.draw.rect(overlay, (0, 0, 0, 255), rect)

        self.r.screen.blit(overlay, (0, 0))

    def _draw_supply_lines(self, game):
        ts = self.r.tsize
        for truck in game.player_units:
            if not isinstance(truck, SupplyTruck) or not truck.is_alive:
                continue
            route = truck.supply_route
            if not route:
                continue
            origin = route["origin"]
            dest = route["dest"]
            if not origin.is_alive or not dest.is_alive:
                continue
            ox = origin.x * ts + ts // 2 + self.r.camera_x
            oy = origin.y * ts + ts // 2 + self.r.camera_y
            dx = dest.x * ts + ts // 2 + self.r.camera_x
            dy = dest.y * ts + ts // 2 + self.r.camera_y
            pygame.draw.line(self.r.screen, (120, 120, 120), (ox, oy), (dx, dy), max(1, ts // 16))
            # Dashed effect: small circles along the line
            for t in range(1, 10, 2):
                frac = t / 10
                cx = int(ox + (dx - ox) * frac)
                cy = int(oy + (dy - oy) * frac)
                pygame.draw.circle(self.r.screen, (120, 120, 120), (cx, cy), max(1, ts // 20))
    
    def _draw_cache_supply_lines(self, game):
        """Отрисовка линий снабжения от погребов и складов к ближайшим юнитам"""
        from ..units import Warehouse, SupplyCache, Infantry, Tank, ReconOperator, FPVOperator, Artillery, RadarEW, SupplyTruck, SoldierUnit
        ts = self.r.tsize
        current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
        
        for source in game.all_units:
            is_cache = isinstance(source, SupplyCache) and source.is_alive and source.build_turns >= source.build_required
            is_warehouse = isinstance(source, Warehouse) and source.is_alive
            if not is_cache and not is_warehouse:
                continue
            if source.faction != current_faction:
                continue
            
            resupply_range = 3 if is_cache else 1
            valid_types = (Infantry, Tank, ReconOperator, FPVOperator, Artillery, RadarEW, SupplyTruck, SoldierUnit)
            
            for unit in game.all_units:
                if not unit.is_alive or unit.faction != current_faction:
                    continue
                if not isinstance(unit, valid_types):
                    continue
                
                dist = abs(unit.x - source.x) + abs(unit.y - source.y)
                if dist > resupply_range or dist == 0:
                    continue
                
                cx1 = source.x * ts + ts // 2 + self.r.camera_x
                cy1 = source.y * ts + ts // 2 + self.r.camera_y
                cx2 = unit.x * ts + ts // 2 + self.r.camera_x
                cy2 = unit.y * ts + ts // 2 + self.r.camera_y
                
                if is_warehouse:
                    color = (100, 150, 200, 150)
                else:
                    color = (100, 180, 100, 120)
                
                for t in range(0, 10, 2):
                    frac1 = t / 10
                    frac2 = (t + 1) / 10
                    x1 = int(cx1 + (cx2 - cx1) * frac1)
                    y1 = int(cy1 + (cy2 - cy1) * frac1)
                    x2 = int(cx1 + (cx2 - cx1) * frac2)
                    y2 = int(cy1 + (cy2 - cy1) * frac2)
                    pygame.draw.line(self.r.screen, color, (x1, y1), (x2, y2), max(1, ts // 20))

    def _draw_trails(self, game):
        ts = self.r.tsize
        # В hot-seat режиме рисуем только путь текущей фракции
        current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
        
        for unit, wps in list(game.waypoints.items()):
            if not unit.is_alive or not wps:
                continue
            # Пропускаем чужие пути в hot-seat
            if game.game_mode == "hotseat" and unit.faction != current_faction:
                continue
            # Цвет в зависимости от фракции
            if unit.faction == config.PLAYER:
                color_reachable = (50, 150, 255)   # Синий
                color_unreachable = (255, 80, 80)   # Красный
            else:
                color_reachable = (255, 100, 100)
                color_unreachable = (255, 50, 50)
            
            max_move = game.get_unit_max_move(unit)
            max_steps = game.get_unit_max_steps(unit)
            pts = [(unit.x, unit.y)] + wps
            move_cost_running = 0
            steps_running = 0
            line_w = max(3, ts // 12)
            
            for i in range(1, len(pts)):
                x1, y1 = pts[i-1]
                x2, y2 = pts[i]
                
                # Стоимость шага
                cell = game.map.get_cell(x2, y2)
                step_cost = 1
                if cell and hasattr(unit, 'get_movement_cost'):
                    step_cost = unit.get_movement_cost(cell.terrain)
                move_cost_running += step_cost
                steps_running += 1
                
                is_reachable = move_cost_running <= max_move and steps_running <= max_steps
                color = color_reachable if is_reachable else color_unreachable
                
                p1 = self._cell_center(x1, y1)
                p2 = self._cell_center(x2, y2)
                pygame.draw.line(self.r.screen, color, p1, p2, line_w)
                if i < len(pts) - 1:
                    pygame.draw.circle(self.r.screen, color, p2, max(3, ts // 10))

    def _cell_center(self, gx, gy):
        ts = self.r.tsize
        return (gx * ts + ts // 2 + self.r.camera_x, gy * ts + ts // 2 + self.r.camera_y)

    def _draw_reachable_cells(self, game):
        if game.phase != config.PHASE_PLANNING:
            return
        unit = game.selected_unit
        if not unit or not unit.is_alive or unit.moved:
            return
        if isinstance(unit, SupplyCache):
            return
        
        # В hot-seat режиме показывать только для юнитов текущей фракции
        if game.game_mode == "hotseat":
            if unit.faction != game.current_player_faction:
                return
        
        max_move = game.get_unit_max_move(unit)
        max_steps = game.get_unit_max_steps(unit)
        
        # Получаем reachable cells с учётом и ОД, и лимита шагов
        reachable = game.map.get_reachable_cells(unit.x, unit.y, max_move, unit, max_steps=max_steps)
        if not reachable:
            return
        
        ts = self.r.tsize
        overlay = pygame.Surface((config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)
        
        for gx, gy in reachable:
            px = gx * ts + self.r.camera_x
            py = gy * ts + self.r.camera_y
            
            # Зелёный для доступных
            pygame.draw.rect(overlay, (50, 200, 50, 70), (px, py, ts, ts))
        
        self.r.screen.blit(overlay, (0, 0))

    def _draw_path_arrow(self, game):
        if game.phase != config.PHASE_PLANNING:
            return
        unit = game.selected_unit
        if not unit or not unit.is_alive or unit.moved:
            return
        if isinstance(unit, SupplyCache):
            return
        
        # В hot-seat режиме показывать только для юнитов текущей фракции
        if game.game_mode == "hotseat":
            if unit.faction != game.current_player_faction:
                return
        
        hovered = game.hovered_cell
        if not hovered:
            return
        gx, gy = hovered
        if gx == unit.x and gy == unit.y:
            return
        max_move = game.get_unit_max_move(unit)
        max_steps = game.get_unit_max_steps(unit)
        # Ищем путь без ограничения по стоимости, чтобы показать полный маршрут
        path = game.map.find_path(unit.x, unit.y, gx, gy, max_cost=99, unit=unit)
        if not path or len(path) < 2:
            return

        ts = self.r.tsize
        
        # Считаем стоимость пути по сегментам и определяем где заканчивается движение
        move_cost_so_far = 0
        steps_so_far = 0
        reachable_idx = len(path) - 1  # По умолчанию весь путь доступен
        
        for i in range(1, len(path)):
            nx, ny = path[i]
            cell = game.map.get_cell(nx, ny)
            step_cost = 1
            if cell and hasattr(unit, 'get_movement_cost'):
                step_cost = unit.get_movement_cost(cell.terrain)
            
            if move_cost_so_far + step_cost > max_move or steps_so_far + 1 > max_steps:
                reachable_idx = i - 1
                break
            move_cost_so_far += step_cost
            steps_so_far += 1
        
        # Цвета: синий = доступно в этом ходу, красный = дальше (будущие ходы)
        COLOR_REACHABLE = (50, 150, 255)     # Синий
        COLOR_UNREACHABLE = (255, 80, 80)    # Красный
        COLOR_ARROW_REACHABLE = (80, 180, 255)
        COLOR_ARROW_UNREACHABLE = (255, 120, 120)
        
        ox, oy = unit.x, unit.y
        move_cost_running = 0
        steps_running = 0
        
        for i in range(1, len(path)):
            nx, ny = path[i]
            cell = game.map.get_cell(nx, ny)
            step_cost = 1
            if cell and hasattr(unit, 'get_movement_cost'):
                step_cost = unit.get_movement_cost(cell.terrain)
            
            move_cost_running += step_cost
            steps_running += 1
            is_reachable = move_cost_running <= max_move and steps_running <= max_steps
            
            # Выбираем цвет в зависимости от доступности
            line_color = COLOR_REACHABLE if is_reachable else COLOR_UNREACHABLE
            arrow_color = COLOR_ARROW_REACHABLE if is_reachable else COLOR_ARROW_UNREACHABLE
            
            cx, cy = self._cell_center(nx, ny)
            ppx, ppy = self._cell_center(ox, oy)
            
            # Толщина линии
            line_w = max(3, ts // 10)
            
            # Рисуем линию сегмента
            pygame.draw.line(self.r.screen, line_color, (ppx, ppy), (cx, cy), line_w)
            
            # Стрелка на середине сегмента
            dx, dy = cx - ppx, cy - ppy
            d = max(1, int((dx*dx + dy*dy)**0.5))
            dxn = dx / d
            dyn = dy / d
            mx_arr = int(ppx + dx * 0.6)
            my_arr = int(ppy + dy * 0.6)
            al = ts // 4
            aw = ts // 8
            bx = int(mx_arr - dxn * al - dyn * aw)
            by = int(my_arr - dyn * al + dxn * aw)
            cx2 = int(mx_arr - dxn * al + dyn * aw)
            cy2 = int(my_arr - dyn * al - dxn * aw)
            pygame.draw.polygon(self.r.screen, arrow_color, [(mx_arr, my_arr), (bx, by), (cx2, cy2)])
            
            # Точка на узле пути (кроме конца)
            if i < len(path) - 1:
                dot_color = line_color
                pygame.draw.circle(self.r.screen, dot_color, (cx, cy), max(3, ts // 8))
            
            # Показываем стоимость местности на клетке
            if ts >= 24 and step_cost != 1:
                cost_text = str(step_cost) if step_cost == int(step_cost) else f"{step_cost:.1f}"
                cost_color = (255, 255, 100) if is_reachable else (255, 150, 150)
                cost_surf = self.r.font_small.render(cost_text, True, cost_color)
                # Позиция текста - немного в стороне от центра
                text_x = cx + ts // 4
                text_y = cy - ts // 4
                # Фон для читаемости
                bg_rect = cost_surf.get_rect(center=(text_x, text_y))
                bg_rect.inflate_ip(4, 2)
                pygame.draw.rect(self.r.screen, (0, 0, 0, 180), bg_rect)
                self.r.screen.blit(cost_surf, cost_surf.get_rect(center=(text_x, text_y)))
            
            # Разделительная линия между доступным и недоступным
            if i == reachable_idx and i < len(path) - 1:
                # Рисуем красную черту на границе
                separator_x = (ppx + cx) // 2
                separator_y = (ppy + cy) // 2
                pygame.draw.circle(self.r.screen, (255, 0, 0), (separator_x, separator_y), max(4, ts // 6))
                pygame.draw.circle(self.r.screen, (255, 255, 255), (separator_x, separator_y), max(4, ts // 6), 1)
            
            ox, oy = nx, ny

        # Draw destination crosshair
        dx, dy = self._cell_center(gx, gy)
        cw = max(4, ts // 4)
        gap = max(2, ts // 8)
        cross_color = (50, 150, 255) if reachable_idx >= len(path) - 1 else (255, 80, 80)
        pygame.draw.line(self.r.screen, cross_color, (dx - cw, dy), (dx - gap, dy), max(1, ts // 16))
        pygame.draw.line(self.r.screen, cross_color, (dx + gap, dy), (dx + cw, dy), max(1, ts // 16))
        pygame.draw.line(self.r.screen, cross_color, (dx, dy - cw), (dx, dy - gap), max(1, ts // 16))
        pygame.draw.line(self.r.screen, cross_color, (dx, dy + gap), (dx, dy + cw), max(1, ts // 16))
        
        # Показываем общую стоимость пути и сколько ОД останется
        if ts >= 20:
            total_cost = 0
            for i in range(1, len(path)):
                nx, ny = path[i]
                cell = game.map.get_cell(nx, ny)
                step_cost = 1
                if cell and hasattr(unit, 'get_movement_cost'):
                    step_cost = unit.get_movement_cost(cell.terrain)
                total_cost += step_cost
            
            info_text = f"Путь: {total_cost} ОД, {len(path)-1} шаг | Лимит: {max_move} ОД, {max_steps} шаг"
            info_color = (100, 200, 100) if total_cost <= max_move else (255, 150, 100)
            info_surf = self.r.font_small.render(info_text, True, info_color)
            self.r.screen.blit(info_surf, (10, config.SCREEN_HEIGHT - 20))

    def _draw_waypoints(self, game):
        unit = game.selected_unit
        if not unit:
            return
        
        # В hot-seat режиме показывать пути только для юнитов текущей фракции
        if game.game_mode == "hotseat":
            if unit.faction != game.current_player_faction:
                return
        
        wps = game.waypoints.get(unit)
        if not wps:
            return
        
        ts = self.r.tsize
        max_move = game.get_unit_max_move(unit)
        max_steps = game.get_unit_max_steps(unit)
        
        # Цвета как в Героях: синий = в этом ходу, красный = дальше
        COLOR_REACHABLE = (50, 150, 255)     # Синий
        COLOR_UNREACHABLE = (255, 80, 80)    # Красный
        
        pts = [(unit.x, unit.y)] + wps
        move_cost_running = 0
        steps_running = 0
        line_w = max(3, ts // 10)
        
        for i in range(1, len(pts)):
            x1, y1 = pts[i-1]
            x2, y2 = pts[i]
            
            # Стоимость шага
            cell = game.map.get_cell(x2, y2)
            step_cost = 1
            if cell and hasattr(unit, 'get_movement_cost'):
                step_cost = unit.get_movement_cost(cell.terrain)
            move_cost_running += step_cost
            steps_running += 1
            
            is_reachable = move_cost_running <= max_move and steps_running <= max_steps
            color = COLOR_REACHABLE if is_reachable else COLOR_UNREACHABLE
            
            p1 = self._cell_center(x1, y1)
            p2 = self._cell_center(x2, y2)
            
            pygame.draw.line(self.r.screen, color, p1, p2, line_w)
            
            # Стрелка на середине
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            d = max(1, int((dx*dx + dy*dy)**0.5))
            dxn, dyn = dx / d, dy / d
            mx_arr = int(p1[0] + dx * 0.5)
            my_arr = int(p1[1] + dy * 0.5)
            al = ts // 4
            aw = ts // 8
            bx = int(mx_arr - dxn * al - dyn * aw)
            by = int(my_arr - dyn * al + dxn * aw)
            cx2 = int(mx_arr - dxn * al + dyn * aw)
            cy2 = int(my_arr - dyn * al - dxn * aw)
            pygame.draw.polygon(self.r.screen, color, [(mx_arr, my_arr), (bx, by), (cx2, cy2)])
            
            # Точка на узле
            if i < len(pts) - 1:
                pygame.draw.circle(self.r.screen, color, p2, max(3, ts // 8))
            
            # Показываем стоимость на клетке если != 1
            if ts >= 24 and step_cost != 1:
                cost_text = str(step_cost) if step_cost == int(step_cost) else f"{step_cost:.1f}"
                cost_surf = self.r.font_small.render(cost_text, True, (255, 255, 100))
                text_x = p2[0] + ts // 4
                text_y = p2[1] - ts // 4
                self.r.screen.blit(cost_surf, cost_surf.get_rect(center=(text_x, text_y)))
            
            # Разделитель на границе доступного
            if not is_reachable and (move_cost_running - step_cost <= max_move or steps_running - 1 <= max_steps):
                sep_x = (p1[0] + p2[0]) // 2
                sep_y = (p1[1] + p2[1]) // 2
                pygame.draw.circle(self.r.screen, (255, 0, 0), (sep_x, sep_y), max(4, ts // 6))
                pygame.draw.circle(self.r.screen, (255, 255, 255), (sep_x, sep_y), max(4, ts // 6), 1)
        
        # Destination marker
        gx, gy = wps[-1]
        dx, dy = self._cell_center(gx, gy)
        cw = max(4, ts // 4)
        gap = max(2, ts // 8)
        dest_color = COLOR_REACHABLE if move_cost_running <= max_move else COLOR_UNREACHABLE
        pygame.draw.line(self.r.screen, dest_color, (dx - cw, dy), (dx - gap, dy), max(1, ts // 16))
        pygame.draw.line(self.r.screen, dest_color, (dx + gap, dy), (dx + cw, dy), max(1, ts // 16))
        pygame.draw.line(self.r.screen, dest_color, (dx, dy - cw), (dx, dy - gap), max(1, ts // 16))
        pygame.draw.line(self.r.screen, dest_color, (dx, dy + gap), (dx, dy + cw), max(1, ts // 16))

    def _draw_pinned_cell(self, game):
        if not game.pinned_cell:
            return
        gx, gy = game.pinned_cell
        cell = game.map.get_cell(gx, gy)
        if not cell:
            return
        ts = self.r.tsize
        px = gx * ts + self.r.camera_x
        py = gy * ts + self.r.camera_y
        rect = pygame.Rect(px, py, ts, ts)
        pygame.draw.rect(self.r.screen, (255, 200, 50), rect, max(2, ts // 12))

    def _draw_artillery_barrage_range(self, game):
        ts = self.r.tsize

        for unit in game.all_units:
            if not isinstance(unit, Artillery) or not unit.is_alive:
                continue
            if not unit.pending_target:
                continue
            tx, ty = unit.pending_target
            cx1 = unit.x * ts + ts // 2 + self.r.camera_x
            cy1 = unit.y * ts + ts // 2 + self.r.camera_y
            cx2 = tx * ts + ts // 2 + self.r.camera_x
            cy2 = ty * ts + ts // 2 + self.r.camera_y
            color = (255, 100, 50, 180)
            for t in range(0, 10, 2):
                frac1 = t / 10
                frac2 = (t + 1) / 10
                x1 = int(cx1 + (cx2 - cx1) * frac1)
                y1 = int(cy1 + (cy2 - cy1) * frac1)
                x2 = int(cx1 + (cx2 - cx1) * frac2)
                y2 = int(cy1 + (cy2 - cy1) * frac2)
                pygame.draw.line(self.r.screen, color, (x1, y1), (x2, y2), max(2, ts // 12))
            px = tx * ts + self.r.camera_x
            py = ty * ts + self.r.camera_y
            pygame.draw.rect(self.r.screen, (255, 50, 50, 150), (px, py, ts, ts), max(2, ts // 10))

        if not game.artillery_barrage_mode:
            return
        unit = game.artillery_barrage_mode
        if not isinstance(unit, Artillery) or not unit.is_alive:
            return

        barrage_range = config.ARTILLERY_BARRAGE_RANGE
        overlay = pygame.Surface((config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)

        for dx in range(-barrage_range, barrage_range + 1):
            for dy in range(-barrage_range, barrage_range + 1):
                if abs(dx) + abs(dy) > barrage_range:
                    continue
                gx = unit.x + dx
                gy = unit.y + dy
                if gx < 0 or gx >= game.map.width or gy < 0 or gy >= game.map.height:
                    continue
                px = gx * ts + self.r.camera_x
                py = gy * ts + self.r.camera_y
                if px + ts < 0 or px > config.SCREEN_WIDTH - config.PANEL_WIDTH or py + ts < 0 or py > config.SCREEN_HEIGHT:
                    continue
                dist = abs(dx) + abs(dy)
                if dist == 0:
                    pygame.draw.rect(overlay, (255, 100, 50, 80), (px, py, ts, ts))
                else:
                    alpha = max(30, 80 - dist * 2)
                    pygame.draw.rect(overlay, (255, 150, 50, alpha), (px, py, ts, ts))

        self.r.screen.blit(overlay, (0, 0))
