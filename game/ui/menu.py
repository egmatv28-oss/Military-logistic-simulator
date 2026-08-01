"""Главное меню игры"""
import math
import random
import pygame
from .. import config
from ..utils.save_load import SaveLoadSystem


def _make_font(size, bold=False):
    """Создать шрифт с поддержкой кириллицы."""
    for name in ("consolas", "segoeui", "segoe ui", "arial", "tahoma", "calibri"):
        try:
            if pygame.font.match_font(name):
                return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            continue
    return pygame.font.SysFont(None, size, bold=bold)


class MenuBackground:
    """Декоративный фон меню: карта из клеток местности и боевых юнитов."""

    def __init__(self):
        self.ts = config.TILE_SIZE
        self.width = config.SCREEN_WIDTH
        self.height = config.SCREEN_HEIGHT
        self.surface = self._build_terrain()
        self.units = self._place_units()
        self.overlay = self._build_overlay()
        self.phases = [i * 1.1 for i in range(len(self.units))]

    def _build_terrain(self):
        ts = self.ts
        w, h = self.width, self.height
        surf = pygame.Surface((w, h))
        surf.fill((24, 34, 44))

        cols = w // ts + 1
        rows = h // ts + 1
        rng = random.Random(2026)
        terrain = [[config.FIELD] * cols for _ in range(rows)]

        # Лесные массивы
        for _ in range(6):
            cx = rng.randint(0, cols - 1)
            cy = rng.randint(0, rows - 1)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx * dx + dy * dy > 6 or rng.random() > 0.7:
                        continue
                    x, y = cx + dx, cy + dy
                    if 0 <= x < cols and 0 <= y < rows:
                        terrain[y][x] = config.FOREST

        # Города
        for _ in range(4):
            x = rng.randint(1, cols - 2)
            y = rng.randint(1, rows - 2)
            terrain[y][x] = config.CITY

        # Река
        river_y = rng.randint(rows // 2 - 1, rows // 2 + 1)
        for x in range(cols):
            terrain[river_y][x] = config.RIVER

        # Горизонтальная дорога
        road_y = rows // 3 + rng.randint(-1, 1)
        for x in range(cols):
            if terrain[road_y][x] != config.RIVER:
                terrain[road_y][x] = config.ROAD

        # Вертикальная дорога
        road_x = cols // 2
        for y in range(rows):
            if terrain[y][road_x] != config.RIVER:
                terrain[y][road_x] = config.ROAD

        for y in range(rows):
            for x in range(cols):
                px, py = x * ts, y * ts
                rect = pygame.Rect(px, py, ts, ts)
                t = terrain[y][x]

                if t == config.FIELD:
                    c = (70, 118, 45) if (x + y) % 2 == 0 else (80, 130, 50)
                    pygame.draw.rect(surf, c, rect)
                elif t == config.FOREST:
                    pygame.draw.rect(surf, (24, 78, 24), rect)
                    off = ts // 6
                    r = ts // 8
                    for i in range(3):
                        ex = px + off + i * off * 2
                        ey = py + off + (i * off) % ts
                        pygame.draw.ellipse(surf, (18, 96, 18), (ex - r, ey - r, r * 2, r * 2))
                        pygame.draw.ellipse(surf, (0, 0, 0), (ex - r, ey - r, r * 2, r * 2), 1)
                elif t == config.CITY:
                    pygame.draw.rect(surf, (104, 88, 66), rect)
                    pygame.draw.rect(surf, (72, 56, 40), rect, 1)
                    bw = ts * 3 // 4
                    bh = ts // 2
                    bx = px + (ts - bw) // 2
                    by = py + ts - bh - 2
                    pygame.draw.rect(surf, (142, 122, 100), (bx, by, bw, bh))
                    pygame.draw.rect(surf, (72, 56, 40), (bx, by, bw, bh), 1)
                    roof = [(bx - 1, by), (px + ts // 2, by - ts // 4), (bx + bw + 1, by)]
                    pygame.draw.polygon(surf, (162, 60, 50), roof)
                    win_y = by + bh // 4
                    win_s = max(2, ts // 10)
                    for wi in range(2):
                        win_x = bx + bw // 3 + wi * bw // 3
                        pygame.draw.rect(surf, (206, 184, 92),
                                         (win_x - win_s, win_y, win_s * 2, win_s))
                elif t == config.ROAD:
                    c = (52, 48, 44) if (x + y) % 2 == 0 else (62, 57, 52)
                    pygame.draw.rect(surf, c, rect)
                elif t == config.RIVER:
                    pygame.draw.rect(surf, (40, 88, 178), rect)
                    for wx in range(0, ts, max(4, ts // 6)):
                        wy = (wx + x * 3 + y * 5) % ts
                        wr = max(2, ts // 12)
                        pygame.draw.ellipse(surf, (52, 108, 198), (px + wx, py + wy, wr * 2, wr))

                pygame.draw.rect(surf, (18, 18, 18), rect, 1)

        return surf

    def _place_units(self):
        p = config.PLAYER
        e = config.ENEMY
        return [
            (2, 2, "warehouse", p),
            (1, 7, "infantry", p),
            (3, 4, "infantry", p),
            (6, 3, "tank", p),
            (4, 10, "truck", p),
            (7, 12, "infantry", p),
            (12, 1, "artillery", p),
            (15, 6, "tank", p),
            (19, 3, "infantry", p),
            (13, 12, "drone", p),
            (9, 13, "radar_ew", p),
            (23, 2, "tank", e),
            (25, 4, "infantry", e),
            (24, 6, "infantry", e),
            (21, 9, "artillery", e),
            (19, 11, "infantry", e),
            (24, 12, "truck", e),
            (17, 13, "drone", e),
        ]

    def _build_overlay(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((6, 10, 18, 180))
        return overlay

    def draw(self, screen):
        screen.blit(self.surface, (0, 0))
        t = pygame.time.get_ticks()
        for (x, y, kind, faction), phase in zip(self.units, self.phases):
            bob = int(2 * math.sin(t * 0.003 + phase))
            self._draw_unit(screen, x, y, kind, faction, bob)
        screen.blit(self.overlay, (0, 0))

    def _unit_color(self, faction):
        return (50, 50, 220) if faction == config.PLAYER else (185, 50, 50)

    def _draw_unit(self, screen, cell_x, cell_y, kind, faction, bob):
        ts = self.ts
        px = cell_x * ts
        py = cell_y * ts + bob
        color = self._unit_color(faction)

        if kind == "warehouse":
            bw = ts * 3 // 4
            bh = ts // 2
            pygame.draw.rect(screen, (100, 100, 120),
                             (px + (ts - bw) // 2, py + ts // 3, bw, bh))
            pygame.draw.rect(screen, (0, 0, 0),
                             (px + (ts - bw) // 2, py + ts // 3, bw, bh), 2)
            points = [
                (px + (ts - bw) // 2 - 2, py + ts // 3),
                (px + ts // 2, py + ts // 6),
                (px + (ts + bw) // 2 + 2, py + ts // 3),
            ]
            pygame.draw.polygon(screen, (130, 50, 50), points)
            pygame.draw.rect(screen, (60, 40, 20),
                             (px + ts // 2 - ts // 10, py + ts * 2 // 3, ts // 5, ts // 4))
        elif kind == "infantry":
            n = 8 if faction == config.PLAYER else 6
            cols = int(n ** 0.5 + 0.5)
            rows = (n + cols - 1) // cols
            w = max(3, ts // (cols + 2))
            h = max(3, ts // (rows + 2))
            gap = max(1, w // 4)
            block_w = cols * w + (cols - 1) * gap
            block_h = rows * h + (rows - 1) * gap
            start_x = px + (ts - block_w) // 2 + w // 2
            start_y = py + (ts - block_h) // 2 + h // 2
            for i in range(n):
                col = i % cols
                row = i // cols
                x = int(start_x + col * (w + gap))
                y = int(start_y + row * (h + gap))
                pygame.draw.rect(screen, color, (x - w // 2, y - h // 2, w, h))
                pygame.draw.rect(screen, (0, 0, 0), (x - w // 2, y - h // 2, w, h), 1)
        elif kind == "tank":
            track_h = max(3, ts // 6)
            track_y = py + ts - track_h - 2
            pygame.draw.rect(screen, (50, 50, 50), (px + 3, track_y, ts - 6, track_h))
            pygame.draw.rect(screen, (0, 0, 0), (px + 3, track_y, ts - 6, track_h), 1)
            body_y = track_y - ts // 4
            pygame.draw.rect(screen, color, (px + 5, body_y, ts - 10, ts // 4))
            pygame.draw.rect(screen, (0, 0, 0), (px + 5, body_y, ts - 10, ts // 4), 1)
            turret_w = ts // 2
            turret_h = ts // 4
            turret = pygame.Rect(px + (ts - turret_w) // 2, body_y - turret_h + 2, turret_w, turret_h)
            pygame.draw.ellipse(screen, color, turret)
            pygame.draw.ellipse(screen, (0, 0, 0), turret, 1)
            barrel = pygame.Rect(px + ts // 2 + turret_w // 4, body_y - turret_h // 2,
                                 ts // 3, max(2, ts // 14))
            pygame.draw.rect(screen, (90, 90, 90), barrel)
            pygame.draw.rect(screen, (0, 0, 0), barrel, 1)
        elif kind == "artillery":
            pygame.draw.rect(screen, color,
                             (px + ts // 6, py + ts // 2, ts * 2 // 3, ts // 3))
            pygame.draw.rect(screen, (0, 0, 0),
                             (px + ts // 6, py + ts // 2, ts * 2 // 3, ts // 3), 1)
            barrel = pygame.Rect(px + ts // 3, py + ts // 6, ts // 3, ts // 2)
            pygame.draw.rect(screen, (100, 100, 100), barrel)
            pygame.draw.rect(screen, (0, 0, 0), barrel, 1)
            wheel_r = max(2, ts // 10)
            pygame.draw.circle(screen, (80, 80, 80), (px + ts // 3, py + ts * 2 // 3), wheel_r)
            pygame.draw.circle(screen, (80, 80, 80), (px + ts * 2 // 3, py + ts * 2 // 3), wheel_r)
        elif kind == "truck":
            cab_w = ts // 4
            cab_h = ts // 3
            cargo_w = ts // 2
            cargo_h = ts * 2 // 5
            pygame.draw.rect(screen, (80, 80, 80), (px + 2, py + ts - cab_h - 4, cab_w, cab_h))
            pygame.draw.rect(screen, color, (px + cab_w, py + ts - cargo_h - 4, cargo_w, cargo_h))
            pygame.draw.rect(screen, (0, 0, 0), (px + 2, py + ts - cab_h - 4, cab_w, cab_h), 1)
            pygame.draw.rect(screen, (0, 0, 0), (px + cab_w, py + ts - cargo_h - 4, cargo_w, cargo_h), 1)
            r = max(2, ts // 14)
            pygame.draw.circle(screen, (40, 40, 40), (px + cab_w // 2, py + ts - 4), r)
            pygame.draw.circle(screen, (40, 40, 40), (px + cab_w + cargo_w // 3, py + ts - 4), r)
            pygame.draw.circle(screen, (40, 40, 40), (px + cab_w + cargo_w * 2 // 3, py + ts - 4), r)
        elif kind == "drone":
            off = ts // 6
            w = max(2, ts // 16)
            pygame.draw.line(screen, color, (px + off, py + off), (px + ts - off, py + ts - off), w)
            pygame.draw.line(screen, color, (px + ts - off, py + off), (px + off, py + ts - off), w)
            cx = px + ts // 2
            cy = py + ts // 2
            pygame.draw.circle(screen, (200, 200, 255), (cx, cy), max(3, ts // 8))
            pygame.draw.circle(screen, color, (cx, cy), max(3, ts // 8), 1)
        elif kind == "radar_ew":
            pygame.draw.rect(screen, color,
                             (px + ts // 6, py + ts // 2, ts * 2 // 3, ts // 3))
            pygame.draw.rect(screen, (0, 0, 0),
                             (px + ts // 6, py + ts // 2, ts * 2 // 3, ts // 3), 1)
            cx = px + ts // 2
            cy = py + ts // 3
            r = ts // 4
            pygame.draw.circle(screen, (150, 150, 150), (cx, cy), r)
            pygame.draw.circle(screen, (0, 0, 0), (cx, cy), r, 1)
            pygame.draw.circle(screen, (100, 200, 200), (cx, cy), r // 2)
            pygame.draw.line(screen, (100, 100, 100), (cx, cy + r), (cx, py + ts // 2),
                             max(1, ts // 16))


class Menu:
    """Главное меню"""

    def __init__(self, screen):
        self.screen = screen
        self.font_large = _make_font(80, bold=True)
        self.font_subtitle = _make_font(32)
        self.font_medium = _make_font(44)
        self.font_hint = _make_font(26)

        self.background = MenuBackground()
        self.selected_option = 0
        self.options = [
            ("Новая игра (vs AI)", "new_game_ai"),
            ("Новая игра (vs Игрок)", "new_game_human"),
            ("Загрузить игру", "load_game"),
            ("Настройки", "settings"),
            ("Выход", "quit"),
        ]

        self.result = None
        self.game_mode = None

    def handle_event(self, event):
        """Обработка событий"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                self.result = self.options[self.selected_option][1]
                return self.result

        return None

    def _blit_text(self, text, font, color, center_x, center_y, shadow=True):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(center_x, center_y))
        if shadow:
            sh = font.render(text, True, (0, 0, 0))
            self.screen.blit(sh, (rect.x + 3, rect.y + 3))
        self.screen.blit(surf, rect)
        return rect

    def _draw_arrow(self, x, y, color):
        h = 13
        w = 16
        points = [(x - w // 2, y - h), (x - w // 2, y + h), (x + w // 2, y)]
        pygame.draw.polygon(self.screen, color, points)

    def draw(self):
        """Отрисовка меню"""
        self.background.draw(self.screen)

        # Заголовок
        self._blit_text("ВОЙНА ЛОГИСТИКИ", self.font_large, (210, 225, 255),
                        config.SCREEN_WIDTH // 2, 140)

        # Подзаголовок
        self._blit_text("Симулятор военного снабжения", self.font_subtitle, (150, 175, 205),
                        config.SCREEN_WIDTH // 2, 205)

        # Опции меню
        y_start = 300
        y_spacing = 60

        for i, (text, _) in enumerate(self.options):
            color = (255, 255, 100) if i == self.selected_option else (205, 205, 205)
            rect = self._blit_text(text, self.font_medium, color,
                                   config.SCREEN_WIDTH // 2, y_start + i * y_spacing)

            # Индикатор выбора
            if i == self.selected_option:
                self._draw_arrow(rect.left - 26, rect.centery, color)

        # Подсказка
        self._blit_text("↑↓ - выбор, Enter - подтвердить", self.font_hint, (120, 140, 170),
                        config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 45, shadow=False)

        pygame.display.flip()

    def get_result(self):
        """Получить результат выбора"""
        return self.result

    def reset(self):
        """Сбросить состояние меню"""
        self.selected_option = 0
        self.result = None


class LoadGameMenu:
    """Меню загрузки игры"""

    def __init__(self, screen):
        self.screen = screen
        self.font_large = _make_font(52, bold=True)
        self.font_medium = _make_font(32)
        self.font_hint = _make_font(24)

        self.background = MenuBackground()
        self.saves = SaveLoadSystem.list_saves()
        self.selected_option = 0
        self.result = None

    def handle_event(self, event):
        """Обработка событий"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.result = "back"
                return self.result
            elif event.key == pygame.K_UP:
                if self.saves:
                    self.selected_option = (self.selected_option - 1) % len(self.saves)
            elif event.key == pygame.K_DOWN:
                if self.saves:
                    self.selected_option = (self.selected_option + 1) % len(self.saves)
            elif event.key == pygame.K_RETURN:
                if self.saves:
                    self.result = self.saves[self.selected_option]['name']
                    return self.result
            elif event.key == pygame.K_DELETE:
                if self.saves:
                    save_name = self.saves[self.selected_option]['name']
                    SaveLoadSystem.delete_save(save_name)
                    self.saves = SaveLoadSystem.list_saves()
                    if self.selected_option >= len(self.saves):
                        self.selected_option = max(0, len(self.saves) - 1)

        return None

    def _blit_text(self, text, font, color, center_x, center_y, shadow=True):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(center_x, center_y))
        if shadow:
            sh = font.render(text, True, (0, 0, 0))
            self.screen.blit(sh, (rect.x + 2, rect.y + 2))
        self.screen.blit(surf, rect)
        return rect

    def _draw_arrow(self, x, y, color):
        h = 11
        w = 14
        points = [(x - w // 2, y - h), (x - w // 2, y + h), (x + w // 2, y)]
        pygame.draw.polygon(self.screen, color, points)

    def draw(self):
        """Отрисовка меню загрузки"""
        self.background.draw(self.screen)

        # Заголовок
        self._blit_text("ЗАГРУЗИТЬ ИГРУ", self.font_large, (210, 225, 255),
                        config.SCREEN_WIDTH // 2, 80)

        if not self.saves:
            self._blit_text("Нет сохранений", self.font_medium, (160, 160, 160),
                            config.SCREEN_WIDTH // 2, 300)
        else:
            y_start = 150
            y_spacing = 50

            for i, save in enumerate(self.saves):
                color = (255, 255, 100) if i == self.selected_option else (205, 205, 205)

                # Имя сохранения и ход
                text = f"Ход {save['turn']} - {save['timestamp'][:19]}"
                rect = self._blit_text(text, self.font_medium, color,
                                       config.SCREEN_WIDTH // 2, y_start + i * y_spacing)

                if i == self.selected_option:
                    self._draw_arrow(rect.left - 22, rect.centery, color)

        # Подсказка
        self._blit_text("↑↓ - выбор, Enter - загрузить, Delete - удалить, Esc - назад",
                        self.font_hint, (120, 140, 170),
                        config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 40, shadow=False)

        pygame.display.flip()

    def get_result(self):
        """Получить результат выбора"""
        return self.result
