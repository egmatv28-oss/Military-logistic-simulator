import pygame
from . import config
from .renderers.map_renderer import MapRenderer
from .renderers.unit_renderer import UnitRenderer
from .renderers.ui_panel_renderer import UIPanelRenderer
from .renderers.effects_renderer import EffectsRenderer
from .renderers.esp_renderer import ESPRenderer


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_small = pygame.font.SysFont("consolas", 11)
        self.font_normal = pygame.font.SysFont("consolas", 14)
        self.font_big = pygame.font.SysFont("consolas", 18)
        self.font_title = pygame.font.SysFont("consolas", 22)
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.dragging = False
        self.drag_start = None
        self.soldier_rects = []
        self.soldier_detail_rects = []
        self.action_buttons_rects = []
        self.hourglass_rect = pygame.Rect(0, 0, 0, 0)

        self._map = MapRenderer(self)
        self._units = UnitRenderer(self)
        self._panel = UIPanelRenderer(self)
        self._effects = EffectsRenderer(self)
        self._esp = ESPRenderer(self)

    @property
    def tsize(self):
        return max(8, int(config.TILE_SIZE * self.zoom))

    def render(self, game):
        self.screen.fill(config.BLACK)
        w, h = config.SCREEN_WIDTH - config.PANEL_WIDTH, config.SCREEN_HEIGHT
        clip_rect = pygame.Rect(0, 0, w, h)
        self.screen.set_clip(clip_rect)

        self._map._draw_map(game)
        self._map._draw_fog(game)
        self._map._draw_supply_lines(game)
        self._map._draw_cache_supply_lines(game)
        self._map._draw_trails(game)
        self._map._draw_reachable_cells(game)
        self._map._draw_artillery_barrage_range(game)
        self._map._draw_path_arrow(game)
        self._map._draw_waypoints(game)
        self._units._draw_units(game)
        self._effects._draw_cargo_transfer_highlights(game)
        self._effects._draw_combat_effects(game)
        self._map._draw_pinned_cell(game)
        self._effects._draw_transfer_mode(game)
        self._effects._draw_cargo_transfer_mode(game)
        self._panel._draw_ui_overlay(game)

        self.screen.set_clip(None)
        self._panel._draw_right_panel(game)
        self._panel._draw_bottom_bar(game)
        self._panel._draw_zoom_indicator()

        if hasattr(game, 'ui') and game.ui and game.ui.cheat_console_open:
            self._esp._draw_cheat_console(game)

        if game.waiting_for_hotseat_switch:
            self._esp._draw_hotseat_switch(game)

        if hasattr(game, 'ui') and game.ui and hasattr(game.ui, 'esp_menu'):
            esp = game.ui.esp_menu
            if esp.is_open:
                esp.draw(self.screen, game, self)
            esp.draw_overlays(self.screen, game, self)

    # ── camera / zoom (called externally by ui_manager / main) ──────

    def zoom_in(self, anchor=None):
        old_ts = self.tsize
        if anchor:
            gx = (anchor[0] - self.camera_x) // old_ts
            gy = (anchor[1] - self.camera_y) // old_ts
        self.zoom = min(config.ZOOM_MAX, self.zoom + config.ZOOM_STEP)
        self._adjust_zoom_anchor(anchor, gx, gy)

    def zoom_out(self, anchor=None):
        old_ts = self.tsize
        if anchor:
            gx = (anchor[0] - self.camera_x) // old_ts
            gy = (anchor[1] - self.camera_y) // old_ts
        self.zoom = max(config.ZOOM_MIN, self.zoom - config.ZOOM_STEP)
        self._adjust_zoom_anchor(anchor, gx, gy)

    def _adjust_zoom_anchor(self, anchor, gx, gy):
        if anchor:
            ts = self.tsize
            self.camera_x = anchor[0] - gx * ts - ts // 2
            self.camera_y = anchor[1] - gy * ts - ts // 2
        self._clamp_camera()

    def handle_scroll(self, dx, dy):
        self.camera_x += dx
        self.camera_y += dy
        self._clamp_camera()

    def _clamp_camera(self):
        ts = self.tsize
        map_pixel_w = config.MAP_WIDTH * ts
        map_pixel_h = config.MAP_HEIGHT * ts
        view_w = config.SCREEN_WIDTH - config.PANEL_WIDTH
        view_h = config.SCREEN_HEIGHT

        self.camera_x = min(0, self.camera_x)
        self.camera_y = min(0, self.camera_y)

        if map_pixel_w > view_w:
            self.camera_x = max(-(map_pixel_w - view_w), self.camera_x)
        else:
            self.camera_x = 0
        if map_pixel_h > view_h:
            self.camera_y = max(-(map_pixel_h - view_h), self.camera_y)
        else:
            self.camera_y = 0

    def screen_to_map(self, screen_x, screen_y):
        ts = self.tsize
        gx = (screen_x - self.camera_x) // ts
        gy = (screen_y - self.camera_y) // ts
        return int(gx), int(gy)
