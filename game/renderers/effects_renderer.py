import random
import pygame
from .. import config
from ..units import ReconDrone, FPVDrone


class EffectsRenderer:
    def __init__(self, renderer):
        self.r = renderer

    def _draw_combat_effects(self, game):
        """Отрисовка визуальных эффектов боя"""
        if not hasattr(game, 'combat_effects'):
            return
        
        ts = self.r.tsize
        for effect in game.combat_effects:
            x, y = effect['x'], effect['y']
            effect_type = effect['type']
            timer = effect['timer']
            
            px = x * ts + self.r.camera_x + ts // 2
            py = y * ts + self.r.camera_y + ts // 2
            
            # Эффект перестрелки пехоты
            if effect_type == "infantry_fight":
                progress = timer / 30.0
                
                # Вспышки выстрелов (несколько маленьких)
                for i in range(3):
                    angle = random.random() * 6.28
                    dist = random.random() * ts * 0.4
                    sx = int(px + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                    sy = int(py + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                    
                    # Жёлтая вспышка выстрела
                    flash_size = int(ts * 0.15 * progress)
                    flash_alpha = int(255 * progress)
                    flash_color = (255, 255, 100, flash_alpha)
                    pygame.draw.circle(self.r.screen, flash_color, (sx, sy), flash_size)
                
                # Трассирующие пули (линии)
                if progress > 0.5:
                    for i in range(2):
                        start_x = px + random.randint(-ts//2, ts//2)
                        start_y = py + random.randint(-ts//2, ts//2)
                        end_x = start_x + random.randint(-ts//3, ts//3)
                        end_y = start_y + random.randint(-ts//3, ts//3)
                        bullet_color = (255, 200, 50, int(200 * progress))
                        pygame.draw.line(self.r.screen, bullet_color, 
                                       (start_x, start_y), (end_x, end_y), 1)
                
                # Эффект пыли/дыма
                dust_size = int(ts * 0.6 * (1 - progress))
                dust_alpha = int(100 * progress)
                dust_color = (150, 130, 100, dust_alpha)
                pygame.draw.circle(self.r.screen, dust_color, (px, py), dust_size)
            
            # Эффект танкового дуэля
            elif effect_type == "tank_duel":
                progress = timer / 30.0
                
                # Большой взрыв
                size = int(ts * 0.8 * progress)
                alpha = int(255 * progress)
                
                # Оранжево-красный взрыв
                color = (255, 100 + int(100 * progress), 0, alpha)
                pygame.draw.circle(self.r.screen, color, (px, py), size)
                
                # Внутренний жёлтый круг
                inner_size = int(size * 0.6)
                inner_color = (255, 255, 100, alpha)
                pygame.draw.circle(self.r.screen, inner_color, (px, py), inner_size)
                
                # Белая вспышка в центре
                if progress > 0.7:
                    white_size = int(size * 0.3)
                    white_color = (255, 255, 255, alpha)
                    pygame.draw.circle(self.r.screen, white_color, (px, py), white_size)
                
                # Искры
                for _ in range(8):
                    angle = random.random() * 6.28
                    dist = random.random() * size * 1.2
                    sx = int(px + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                    sy = int(py + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                    spark_color = (255, 200, 50, alpha)
                    pygame.draw.circle(self.r.screen, spark_color, (sx, sy), 2)
                
                # Дым (поднимается вверх)
                for i in range(3):
                    smoke_y = py - int(ts * 0.3 * i * progress)
                    smoke_size = int(ts * 0.2 * (1 + i * 0.3))
                    smoke_alpha = int(80 * progress * (1 - i * 0.2))
                    smoke_color = (100, 100, 100, smoke_alpha)
                    pygame.draw.circle(self.r.screen, smoke_color, (px, smoke_y), smoke_size)
            
            # Эффект танк vs пехота
            elif effect_type == "tank_vs_infantry":
                progress = timer / 30.0
                
                # Разрыв картечи (несколько маленьких взрывов)
                for i in range(5):
                    angle = random.random() * 6.28
                    dist = random.random() * ts * 0.5
                    sx = int(px + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                    sy = int(py + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                    
                    explosion_size = int(ts * 0.2 * progress)
                    explosion_alpha = int(200 * progress)
                    explosion_color = (255, 150, 0, explosion_alpha)
                    pygame.draw.circle(self.r.screen, explosion_color, (sx, sy), explosion_size)
                
                # Пыль от взрывов
                dust_size = int(ts * 0.8 * progress)
                dust_alpha = int(60 * progress)
                dust_color = (180, 160, 120, dust_alpha)
                pygame.draw.circle(self.r.screen, dust_color, (px, py), dust_size)
            
            # Эффект артиллерийского взрыва (больше и мощнее)
            elif effect_type == "artillery":
                progress = timer / 30.0
                size = int(ts * 1.2 * progress)
                alpha = int(255 * progress)
                
                # Большой оранжевый взрыв
                color = (255, 150, 0, alpha)
                pygame.draw.circle(self.r.screen, color, (px, py), size)
                
                # Яркий центр
                inner_size = int(size * 0.5)
                inner_color = (255, 255, 200, alpha)
                pygame.draw.circle(self.r.screen, inner_color, (px, py), inner_size)
                
                # Дым
                smoke_size = int(size * 0.8)
                smoke_color = (100, 100, 100, alpha // 2)
                pygame.draw.circle(self.r.screen, smoke_color, (px, py - size // 3), smoke_size)
                
                # Осколки
                for _ in range(8):
                    angle = random.random() * 6.28
                    dist = random.random() * size * 1.5
                    sx = int(px + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                    sy = int(py + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                    spark_color = (200, 100, 0, alpha)
                    pygame.draw.circle(self.r.screen, spark_color, (sx, sy), 3)
            
            # Эффект полёта снаряда
            elif effect_type == "artillery_shell":
                max_timer = effect.get('max_timer', 20)
                progress = 1.0 - (timer / max_timer)  # 0 → 1 (от источника к цели)
                
                src_x, src_y = effect.get('src_x', x), effect.get('src_y', y)
                spx = src_x * ts + self.r.camera_x + ts // 2
                spy = src_y * ts + self.r.camera_y + ts // 2
                
                # Текущая позиция снаряда
                cur_x = spx + (px - spx) * progress
                cur_y = spy + (py - spy) * progress
                
                # Хвост (линия позади снаряда)
                tail_len = 0.15
                tail_x = spx + (px - spx) * max(0, progress - tail_len)
                tail_y = spy + (py - spy) * max(0, progress - tail_len)
                
                # Оранжевый хвост
                pygame.draw.line(self.r.screen, (255, 180, 50), 
                               (int(tail_x), int(tail_y)), 
                               (int(cur_x), int(cur_y)), 2)
                
                # Яркая головка снаряда
                pygame.draw.circle(self.r.screen, (255, 255, 200), (int(cur_x), int(cur_y)), 3)
                pygame.draw.circle(self.r.screen, (255, 200, 50), (int(cur_x), int(cur_y)), 5, 1)
            
            # Эффект FPV удара
            elif effect_type == "fpv_strike":
                progress = timer / 30.0
                
                # Контролируемый взрыв (точечный)
                size = int(ts * 0.6 * progress)
                alpha = int(255 * progress)
                
                # Красно-оранжевый взрыв
                color = (255, 50, 0, alpha)
                pygame.draw.circle(self.r.screen, color, (px, py), size)
                
                # Белая вспышка
                white_size = int(size * 0.4)
                white_color = (255, 255, 255, alpha)
                pygame.draw.circle(self.r.screen, white_color, (px, py), white_size)
                
                # Маленькие осколки
                for _ in range(4):
                    angle = random.random() * 6.28
                    dist = random.random() * size
                    sx = int(px + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                    sy = int(py + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                    pygame.draw.circle(self.r.screen, (200, 100, 0, alpha), (sx, sy), 2)
            
            # Эффект рикошета
            elif effect_type == "ricochet":
                progress = timer / 30.0
                
                # Искра от рикошета
                spark_size = int(ts * 0.3 * progress)
                spark_alpha = int(255 * progress)
                
                # Яркая бело-жёлтая искра
                spark_color = (255, 255, 200, spark_alpha)
                pygame.draw.circle(self.r.screen, spark_color, (px, py), spark_size)
                
                # Линия рикошета (отскок)
                angle = random.random() * 6.28
                end_x = int(px + ts * 0.4 * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                end_y = int(py + ts * 0.4 * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                ricochet_color = (255, 200, 100, spark_alpha)
                pygame.draw.line(self.r.screen, ricochet_color, (px, py), (end_x, end_y), 2)
                
                # Маленькие искры вдоль линии
                for i in range(3):
                    t = (i + 1) / 4
                    spark_x = int(px + (end_x - px) * t)
                    spark_y = int(py + (end_y - py) * t)
                    pygame.draw.circle(self.r.screen, (255, 255, 100, spark_alpha), 
                                     (spark_x, spark_y), 1)
            
            # Эффект передачи ресурсов
            elif effect_type == "resource_transfer":
                progress = timer / 20.0
                
                # Линия от источника к цели
                source = effect.get('source')
                target = effect.get('target')
                if source and target:
                    sx = source.x * ts + ts // 2 + self.r.camera_x
                    sy = source.y * ts + ts // 2 + self.r.camera_y
                    tx = target.x * ts + ts // 2 + self.r.camera_x
                    ty = target.y * ts + ts // 2 + self.r.camera_y
                    
                    # Зелёная линия
                    line_color = (50, 255, 50, int(200 * progress))
                    pygame.draw.line(self.r.screen, line_color, (sx, sy), (tx, ty), 2)
                    
                    # Движущаяся точка (ресурс)
                    dot_x = int(sx + (tx - sx) * (1 - progress))
                    dot_y = int(sy + (ty - sy) * (1 - progress))
                    dot_color = (100, 255, 100, int(255 * progress))
                    pygame.draw.circle(self.r.screen, dot_color, (dot_x, dot_y), max(3, ts // 6))
                    
                    # Маленькие частицы вокруг точки
                    for i in range(3):
                        angle = random.random() * 6.28
                        dist = random.random() * ts * 0.2
                        px_part = int(dot_x + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
                        py_part = int(dot_y + dist * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
                        pygame.draw.circle(self.r.screen, (100, 200, 100, int(150 * progress)), (px_part, py_part), 1)

    def _draw_cargo_transfer_highlights(self, game):
        """Отрисовка подсветки при передаче груза"""
        if game.cargo_transfer_timer <= 0:
            return
        
        ts = self.r.tsize
        progress = game.cargo_transfer_timer / 20.0
        
        # Подсветка грузовика (зелёная)
        if game.cargo_transfer_source and game.cargo_transfer_source.is_alive:
            src = game.cargo_transfer_source
            px = src.x * ts + self.r.camera_x
            py = src.y * ts + self.r.camera_y
            alpha = int(255 * progress)
            color = (0, 255, 0, alpha)
            rect = pygame.Rect(px - 2, py - 2, ts + 4, ts + 4)
            pygame.draw.rect(self.r.screen, color, rect, 3)
        
        # Подсветка цели (синяя)
        if game.cargo_transfer_target and game.cargo_transfer_target.is_alive:
            tgt = game.cargo_transfer_target
            px = tgt.x * ts + self.r.camera_x
            py = tgt.y * ts + self.r.camera_y
            alpha = int(255 * progress)
            color = (50, 150, 255, alpha)
            rect = pygame.Rect(px - 2, py - 2, ts + 4, ts + 4)
            pygame.draw.rect(self.r.screen, color, rect, 3)

    def _draw_transfer_mode(self, game):
        """Отрисовка подсветки в режиме передачи ресурсов"""
        if not game.transfer_mode or not game.transfer_source:
            return
        
        ts = self.r.tsize
        source = game.transfer_source
        overlay = pygame.Surface((config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)
        
        # Подсвечиваем источник (жёлтый)
        sx = source.x * ts + self.r.camera_x
        sy = source.y * ts + self.r.camera_y
        pygame.draw.rect(overlay, (255, 255, 0, 100), (sx, sy, ts, ts))
        pygame.draw.rect(overlay, (255, 255, 0), (sx, sy, ts, ts), 3)
        
        # Подсвечиваем соседние юниты (зелёный) - потенциальные цели
        for unit in game.all_units:
            if not unit.is_alive or unit is source:
                continue
            if unit.faction != source.faction:
                continue
            dist = abs(unit.x - source.x) + abs(unit.y - source.y)
            if dist <= 1:
                ux = unit.x * ts + self.r.camera_x
                uy = unit.y * ts + self.r.camera_y
                pygame.draw.rect(overlay, (50, 255, 50, 80), (ux, uy, ts, ts))
                pygame.draw.rect(overlay, (50, 255, 50), (ux, uy, ts, ts), 2)
        
        self.r.screen.blit(overlay, (0, 0))
        
        # Текст подсказки
        hint = self.r.font_normal.render("Кликните на зелёный юнит для передачи", True, (255, 255, 200))
        self.r.screen.blit(hint, (10, config.SCREEN_HEIGHT - 40))

    def _draw_cargo_transfer_mode(self, game):
        """Отрисовка подсветки в режиме передачи груза"""
        if not game.cargo_transfer_mode or not game.cargo_transfer_truck:
            return
        
        ts = self.r.tsize
        truck = game.cargo_transfer_truck
        overlay = pygame.Surface((config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)
        
        # Подсвечиваем грузовик (зелёный)
        sx = truck.x * ts + self.r.camera_x
        sy = truck.y * ts + self.r.camera_y
        pygame.draw.rect(overlay, (0, 255, 0, 100), (sx, sy, ts, ts))
        pygame.draw.rect(overlay, (0, 255, 0), (sx, sy, ts, ts), 3)
        
        # Подсвечиваем соседние юниты (синий) - потенциальные цели
        for unit in game.all_units:
            if not unit.is_alive or unit is truck:
                continue
            if unit.faction != truck.faction:
                continue
            if isinstance(unit, (ReconDrone, FPVDrone)):
                continue
            dist = abs(unit.x - truck.x) + abs(unit.y - truck.y)
            if dist <= 1:
                ux = unit.x * ts + self.r.camera_x
                uy = unit.y * ts + self.r.camera_y
                pygame.draw.rect(overlay, (50, 100, 255, 80), (ux, uy, ts, ts))
                pygame.draw.rect(overlay, (50, 100, 255), (ux, uy, ts, ts), 2)
        
        self.r.screen.blit(overlay, (0, 0))
        
        # Текст подсказки
        cargo_name = config.CARGO_NAMES.get(game.cargo_transfer_type, "")
        hint = self.r.font_normal.render(f"Кликните на синий юнит для передачи {cargo_name} (ESC - отмена)", True, (255, 255, 200))
        self.r.screen.blit(hint, (10, config.SCREEN_HEIGHT - 40))
