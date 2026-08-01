"""ESP меню - дополнительная информация о юнитах, ресурсах и командах"""
import pygame
from .. import config
from ..units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, SupplyCache, Artillery, SoldierUnit
from ..utils.save_load import SaveLoadSystem


class ESPMenu:
    """Меню ESP (Extra Sensory Perception) - показывает скрытую информацию"""
    
    def __init__(self):
        self.is_open = False
        self.selected_option = 0
        self.current_tab = 0  # 0 - ESP, 1 - Команды, 2 - Сохранение
        
        # ESP toggles
        self.show_all_enemies = False
        self.show_enemy_stats = False
        self.show_friendly_hp = False
        self.show_resources = False
        self.show_attack_ranges = False
        self.show_unit_names = False
        self.show_detection_range = False
        
        # Вкладки меню
        self.tabs = ["ESP", "Команды", "Сохранение", "Состав"]
        
        # Опции ESP
        self.esp_options = [
            ("Все враги (сквозь туман)", "toggle_enemies"),
            ("Статы врагов (HP/Боезапас)", "toggle_enemy_stats"),
            ("HP союзников", "toggle_friendly_hp"),
            ("Ресурсы на складах", "toggle_resources"),
            ("Радиусы атаки", "toggle_attack_ranges"),
            ("Имена юнитов", "toggle_unit_names"),
            ("Радиус обнаружения", "toggle_detection_range"),
        ]
        
        # Команды консоли
        self.cheat_commands = [
            ("fog", "Убрать туман войны"),
            ("infantry", "Добавить пехоту"),
            ("tank", "Добавить танк"),
            ("drone", "Добавить разведдрон"),
            ("resources", "Пополнить ресурсы склада"),
            ("win", "Мгновенная победа"),
            ("lose", "Мгновенное поражение"),
            ("turn", "Пропустить 10 ходов"),
            ("reveal", "Показать всех врагов"),
        ]
        
        # Сохранения
        self.saves = []
        self.selected_save = 0
    
    def toggle(self):
        """Открыть/закрыть меню"""
        self.is_open = not self.is_open
        if self.is_open:
            self.selected_option = 0
            self.current_tab = 0
            self._refresh_saves()
    
    def _refresh_saves(self):
        """Обновить список сохранений"""
        self.saves = SaveLoadSystem.list_saves()
    
    def handle_event(self, event):
        """Обработка событий меню"""
        if not self.is_open:
            return
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                self.is_open = False
                return
            
            # Переключение вкладок
            if event.key == pygame.K_LEFT:
                self.current_tab = (self.current_tab - 1) % len(self.tabs)
                self.selected_option = 0
                if self.current_tab == 2:
                    self._refresh_saves()
                return
            elif event.key == pygame.K_RIGHT:
                self.current_tab = (self.current_tab + 1) % len(self.tabs)
                self.selected_option = 0
                if self.current_tab == 2:
                    self._refresh_saves()
                return
            
            # Навигация по опциям
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % self._get_option_count()
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % self._get_option_count()
            elif event.key == pygame.K_RETURN:
                self._select_option()
    
    def _get_option_count(self):
        """Получить количество опций на текущей вкладке"""
        if self.current_tab == 0:
            return len(self.esp_options)
        elif self.current_tab == 1:
            return len(self.cheat_commands)
        elif self.current_tab == 2:
            # Кнопка сохранения + список сохранений
            return (len(self.saves) + 1) if self.saves else 1
        elif self.current_tab == 3:
            return 1
        return 0
    
    def _select_option(self):
        """Выбрать опцию"""
        if self.current_tab == 0:
            # ESP toggles
            action = self.esp_options[self.selected_option][1]
            self._toggle_option(action)
        elif self.current_tab == 2:
            if self.selected_option == 0:
                # Кнопка "СОХРАНИТЬ ИГРУ" — сохранение обрабатывается в main.py
                return
            # Загрузка сохранения
            save_idx = self.selected_option - 1
            if self.saves and 0 <= save_idx < len(self.saves):
                save_name = self.saves[save_idx]['name']
                self._load_game(save_name)
    
    def _toggle_option(self, action):
        """Переключить опцию ESP"""
        if action == "toggle_enemies":
            self.show_all_enemies = not self.show_all_enemies
        elif action == "toggle_enemy_stats":
            self.show_enemy_stats = not self.show_enemy_stats
        elif action == "toggle_friendly_hp":
            self.show_friendly_hp = not self.show_friendly_hp
        elif action == "toggle_resources":
            self.show_resources = not self.show_resources
        elif action == "toggle_attack_ranges":
            self.show_attack_ranges = not self.show_attack_ranges
        elif action == "toggle_unit_names":
            self.show_unit_names = not self.show_unit_names
        elif action == "toggle_detection_range":
            self.show_detection_range = not self.show_detection_range
    
    def _load_game(self, save_name):
        """Загрузить игру (возвращает имя сохранения для обработки снаружи)"""
        self.pending_load = save_name
        self.is_open = False
    
    def draw(self, screen, game, renderer):
        """Отрисовка меню ESP"""
        if not self.is_open:
            return
        
        # Размеры меню
        menu_width = 400
        menu_height = 500 if self.current_tab == 3 else 380
        menu_x = 10
        menu_y = 10
        
        # Полупрозрачный фон
        overlay = pygame.Surface((menu_width, menu_height), pygame.SRCALPHA)
        overlay.fill((20, 20, 40, 230))
        screen.blit(overlay, (menu_x, menu_y))
        
        # Рамка
        pygame.draw.rect(screen, (100, 150, 255), (menu_x, menu_y, menu_width, menu_height), 2)
        
        # Шрифты
        font_title = pygame.font.SysFont("consolas", 18, bold=True)
        font_text = pygame.font.SysFont("consolas", 14)
        font_small = pygame.font.SysFont("consolas", 12)
        
        # Заголовок
        title = font_title.render("ESP МЕНЮ", True, (100, 200, 255))
        screen.blit(title, (menu_x + 10, menu_y + 10))
        
        # Вкладки
        tab_y = menu_y + 35
        tab_x = menu_x + 10
        for i, tab_name in enumerate(self.tabs):
            if i == self.current_tab:
                color = (255, 255, 100)
                tab_text = f"[{tab_name}]"
            else:
                color = (150, 150, 150)
                tab_text = f" {tab_name} "
            surf = font_text.render(tab_text, True, color)
            screen.blit(surf, (tab_x, tab_y))
            tab_x += surf.get_width() + 15
        
        # Разделитель
        pygame.draw.line(screen, (80, 80, 100), (menu_x + 10, tab_y + 20), (menu_x + menu_width - 10, tab_y + 20))
        
        # Содержимое вкладок
        content_y = tab_y + 30
        
        if self.current_tab == 0:
            # Вкладка ESP
            self._draw_esp_tab(screen, menu_x, content_y, menu_width, font_text)
        elif self.current_tab == 1:
            # Вкладка Команды
            self._draw_commands_tab(screen, menu_x, content_y, menu_width, font_text, font_small)
        elif self.current_tab == 2:
            # Вкладка Сохранение
            self._draw_save_tab(screen, menu_x, content_y, menu_width, font_text, game)
        elif self.current_tab == 3:
            # Вкладка Состав
            self._draw_roster_tab(screen, menu_x, menu_y, content_y, menu_width, menu_height, font_text, font_small, game)
        
        # Подсказка внизу
        hint = font_small.render("←/→ вкладки | Tab/Esc закрыть | Enter выбрать", True, (100, 100, 130))
        screen.blit(hint, (menu_x + 10, menu_y + menu_height - 20))
    
    def _draw_esp_tab(self, screen, menu_x, y, menu_width, font_text):
        """Отрисовка вкладки ESP"""
        for i, (text, _) in enumerate(self.esp_options):
            # Получаем статус
            enabled = self._get_esp_status(i)
            
            # Цвет текста
            if i == self.selected_option:
                color = (255, 255, 100)
                prefix = ">"
            else:
                color = (200, 200, 200)
                prefix = " "
            
            status = "[ON]" if enabled else "[OFF]"
            status_color = (100, 255, 100) if enabled else (255, 100, 100)
            
            line = f"{prefix} {text}"
            surf = font_text.render(line, True, color)
            screen.blit(surf, (menu_x + 10, y))
            
            status_surf = font_text.render(status, True, status_color)
            screen.blit(status_surf, (menu_x + menu_width - 60, y))
            
            y += 22
    
    def _get_esp_status(self, index):
        """Получить статус ESP опции по индексу"""
        statuses = [
            self.show_all_enemies,
            self.show_enemy_stats,
            self.show_friendly_hp,
            self.show_resources,
            self.show_attack_ranges,
            self.show_unit_names,
            self.show_detection_range,
        ]
        return statuses[index] if index < len(statuses) else False
    
    def _draw_commands_tab(self, screen, menu_x, y, menu_width, font_text, font_small):
        """Отрисовка вкладки команд"""
        # Заголовок
        header = font_text.render("Доступные команды (Shift+C):", True, (150, 200, 255))
        screen.blit(header, (menu_x + 10, y))
        y += 20
        
        for i, (cmd, desc) in enumerate(self.cheat_commands):
            if i == self.selected_option:
                color = (255, 255, 100)
                prefix = ">"
            else:
                color = (200, 200, 200)
                prefix = " "
            
            cmd_text = f"{prefix} {cmd}"
            cmd_surf = font_text.render(cmd_text, True, (100, 255, 100))
            screen.blit(cmd_surf, (menu_x + 10, y))
            
            desc_surf = font_small.render(f" - {desc}", True, (180, 180, 180))
            screen.blit(desc_surf, (menu_x + 80, y + 2))
            
            y += 20
    
    def _draw_save_tab(self, screen, menu_x, y, menu_width, font_text, game):
        """Отрисовка вкладки сохранения"""
        # Кнопка сохранения
        save_text = "СОХРАНИТЬ ИГРУ (Enter)"
        if self.selected_option == 0:
            color = (100, 255, 100)
            prefix = ">"
        else:
            color = (200, 200, 200)
            prefix = " "
        
        surf = font_text.render(f"{prefix} {save_text}", True, color)
        screen.blit(surf, (menu_x + 10, y))
        y += 25
        
        # Разделитель
        pygame.draw.line(screen, (80, 80, 100), (menu_x + 10, y), (menu_x + menu_width - 10, y))
        y += 10
        
        # Список сохранений
        header = font_text.render("Загрузить сохранение:", True, (150, 200, 255))
        screen.blit(header, (menu_x + 10, y))
        y += 20
        
        if not self.saves:
            no_saves = font_text.render("Нет сохранений", True, (150, 150, 150))
            screen.blit(no_saves, (menu_x + 10, y))
        else:
            for i, save in enumerate(self.saves):
                save_idx = i + 1  # +1 потому что 0 - кнопка сохранения
                if save_idx == self.selected_option:
                    color = (255, 255, 100)
                    prefix = ">"
                else:
                    color = (180, 180, 180)
                    prefix = " "
                
                text = f"{prefix} Ход {save['turn']} - {save['timestamp'][:10]}"
                surf = font_text.render(text, True, color)
                screen.blit(surf, (menu_x + 10, y))
                y += 20
    
    def _draw_roster_tab(self, screen, menu_x, menu_y, y, menu_width, menu_height, font_text, font_small, game):
        """Отрисовка вкладки состава — живые и мёртвые солдаты"""
        from ..units import Soldier, SoldierUnit

        all_alive = []
        dead_total = Soldier._global_dead_count

        for unit in game.all_units:
            if not unit.is_alive:
                continue
            if hasattr(unit, 'soldiers_list'):
                for s in unit.soldiers_list:
                    if s.is_alive:
                        all_alive.append((unit, s))
            elif isinstance(unit, SoldierUnit) and unit.soldier.is_alive:
                all_alive.append((unit, unit.soldier))

        alive_total = len(all_alive)
        header = f"Живых: {alive_total}  |  Мертвых: {dead_total}  |  Всего: {alive_total + dead_total}"
        surf = font_text.render(header, True, (100, 200, 255))
        screen.blit(surf, (menu_x + 10, y))
        y += 22

        # Разделитель
        pygame.draw.line(screen, (80, 80, 100), (menu_x + 10, y), (menu_x + menu_width - 10, y))
        y += 10

        # Список живых солдат
        alive_label = font_text.render("Живые:", True, (100, 255, 100))
        screen.blit(alive_label, (menu_x + 10, y))
        y += 18

        for unit, soldier in all_alive:
            if y > menu_y + menu_height - 30:
                break
            name = soldier.short_name
            role = soldier.role
            hp = soldier.health
            unit_name = (unit.name[:10] if not isinstance(unit, SoldierUnit) else "перенос")
            line = f"  {name} ({role}) - {hp}% [в {unit_name}]"
            color = (200, 255, 200) if hp > 50 else (255, 255, 150) if hp > 25 else (255, 150, 150)
            surf = font_small.render(line, True, color)
            screen.blit(surf, (menu_x + 10, y))
            y += 13

    def handle_save(self, game):
        """Обработать сохранение игры"""
        if not self.is_open and hasattr(self, 'pending_save') and self.pending_save:
            self.pending_save = False
            slot_name = f"save_turn_{game.turn}"
            SaveLoadSystem.save_game(game, slot_name)
            game.message = f"Игра сохранена: {slot_name}"
            return True
        return False
    
    def handle_load(self):
        """Обработать загрузку игры"""
        if hasattr(self, 'pending_load') and self.pending_load:
            save_name = self.pending_load
            self.pending_load = None
            return save_name
        return None
    
    def draw_overlays(self, screen, game, renderer):
        """Отрисовка ESP оверлеев на карте"""
        if not self.show_all_enemies and not self.show_enemy_stats and \
           not self.show_friendly_hp and not self.show_resources and \
           not self.show_attack_ranges and not self.show_unit_names and \
           not self.show_detection_range:
            return
        
        ts = renderer.tsize
        font_small = pygame.font.SysFont("consolas", 10)
        
        for unit in game.all_units:
            if not unit.is_alive:
                continue
            
            # Определяем текущую фракцию
            current_faction = game.current_player_faction if game.game_mode == "hotseat" else config.PLAYER
            enemy_faction = config.ENEMY if current_faction == config.PLAYER else config.PLAYER
            
            is_enemy = unit.faction == enemy_faction
            is_friendly = unit.faction == current_faction
            
            # Позиция юнита на экране
            px = unit.x * ts + renderer.camera_x
            py = unit.y * ts + renderer.camera_y
            
            # Пропускаем если вне экрана
            if px < -ts or px > config.SCREEN_WIDTH or py < -ts or py > config.SCREEN_HEIGHT:
                continue
            
            # Показать всех врагов (сквозь туман)
            if self.show_all_enemies and is_enemy:
                # Красный оверлей для врагов
                overlay = pygame.Surface((ts, ts), pygame.SRCALPHA)
                overlay.fill((255, 50, 50, 60))
                screen.blit(overlay, (px, py))
                
                # Рамка
                pygame.draw.rect(screen, (255, 50, 50), (px, py, ts, ts), 1)
            
            # Показать статы врагов
            if self.show_enemy_stats and is_enemy:
                self._draw_unit_stats(screen, unit, px, py, ts, font_small, (255, 100, 100), game.map)
            
            # Показать HP союзников
            if self.show_friendly_hp and is_friendly:
                self._draw_hp_bar(screen, unit, px, py, ts)
            
            # Показать ресурсы на складах/погребах
            if self.show_resources and isinstance(unit, (Warehouse, SupplyCache)):
                self._draw_resources(screen, unit, px, py, ts, font_small)
            
            # Показать радиусы атаки
            if self.show_attack_ranges and isinstance(unit, (Infantry, Tank, Artillery)):
                self._draw_attack_range(screen, unit, px, py, ts, renderer)
            
            # Показать имена юнитов
            if self.show_unit_names:
                name_color = (255, 100, 100) if is_enemy else (100, 200, 100)
                name_surf = font_small.render(unit.name[:12], True, name_color)
                screen.blit(name_surf, (px, py - 12))
            
            # Показать радиус обнаружения
            if self.show_detection_range and is_friendly:
                self._draw_detection_range(screen, unit, px, py, ts, renderer)
    
    def _draw_unit_stats(self, screen, unit, px, py, ts, font, color, game_map=None):
        """Отрисовка статов юнита"""
        y_offset = py + ts + 2
        
        if isinstance(unit, Infantry):
            entrench = 0
            if game_map:
                cell = game_map.get_cell(unit.x, unit.y)
                entrench = cell.entrenchment
            elif hasattr(unit, 'game_map') and unit.game_map:
                cell = unit.game_map.get_cell(unit.x, unit.y)
                entrench = cell.entrenchment
            stats = [
                f"HP:{unit.soldiers}/{unit.max_soldiers}",
                f"AMO:{unit.ammo}",
                f"ENT:{entrench}%",
            ]
        elif isinstance(unit, Tank):
            stats = [
                f"HP:{unit.crew}/{unit.max_crew}",
                f"ARM:{unit.armor}",
                f"AMO:{unit.ammo}",
            ]
        elif isinstance(unit, Artillery):
            stats = [
                f"HP:{unit.crew}/{unit.max_crew}",
                f"AMO:{unit.ammo}",
            ]
        elif isinstance(unit, ReconDrone):
            stats = [f"BAT:{unit.battery}"]
        elif isinstance(unit, SupplyTruck):
            stats = [f"W:{unit.total_weight}/{unit.max_weight}"]
        elif isinstance(unit, Warehouse):
            stats = [
                f"S:{unit.supplies}",
                f"A:{unit.ammo}",
                f"F:{unit.fuel}",
            ]
        else:
            return
        
        for i, stat in enumerate(stats):
            surf = font.render(stat, True, color)
            screen.blit(surf, (px, y_offset + i * 11))
    
    def _draw_hp_bar(self, screen, unit, px, py, ts):
        """Отрисовка полоски HP"""
        # Определяем текущий HP процент
        if isinstance(unit, Infantry):
            hp_pct = unit.soldiers / unit.max_soldiers
        elif isinstance(unit, Tank):
            hp_pct = unit.crew / unit.max_crew
        elif isinstance(unit, Artillery):
            hp_pct = unit.crew / unit.max_crew
        elif isinstance(unit, ReconDrone):
            hp_pct = unit.battery / unit.max_battery
        elif isinstance(unit, SupplyTruck):
            hp_pct = unit.fuel / unit.max_fuel if unit.max_fuel > 0 else 1
        else:
            return
        
        # Цвет в зависимости от HP
        if hp_pct > 0.6:
            bar_color = (100, 255, 100)
        elif hp_pct > 0.3:
            bar_color = (255, 255, 100)
        else:
            bar_color = (255, 100, 100)
        
        # Полоска
        bar_width = ts - 4
        bar_height = 3
        bar_x = px + 2
        bar_y = py + ts - 5
        
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, bar_color, (bar_x, bar_y, int(bar_width * hp_pct), bar_height))
    
    def _draw_resources(self, screen, unit, px, py, ts, font):
        """Отрисовка ресурсов на складе/погребе"""
        if isinstance(unit, Warehouse):
            resources = [
                f"П:{unit.supplies}",
                f"Б:{unit.ammo}",
                f"Т:{unit.fuel}",
                f"Ба:{unit.batteries}",
            ]
        elif isinstance(unit, SupplyCache):
            if unit.build_turns < unit.build_required:
                resources = [f"СТР:{unit.build_turns}/{unit.build_required}"]
            else:
                resources = [
                    f"П:{unit.supplies}",
                    f"Б:{unit.ammo}",
                    f"Т:{unit.fuel}",
                ]
        else:
            return
        
        color = (100, 200, 255) if unit.faction == config.PLAYER else (255, 150, 100)
        for i, res in enumerate(resources):
            surf = font.render(res, True, color)
            screen.blit(surf, (px, py - 12 - i * 11))
    
    def _draw_attack_range(self, screen, unit, px, py, ts, renderer):
        """Отрисовка радиуса атаки"""
        if isinstance(unit, Artillery):
            attack_range = config.ARTILLERY_ATTACK_RANGE
        elif isinstance(unit, Tank):
            attack_range = config.TANK_ATTACK_RANGE
        elif isinstance(unit, Infantry):
            attack_range = config.INFANTRY_ATTACK_RANGE
        else:
            return
        
        # Рисуем круг радиуса атаки
        center_x = px + ts // 2
        center_y = py + ts // 2
        radius = attack_range * ts
        
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (255, 100, 100, 30), (center_x, center_y), radius)
        pygame.draw.circle(overlay, (255, 100, 100, 80), (center_x, center_y), radius, 1)
        screen.blit(overlay, (0, 0))
    
    def _draw_detection_range(self, screen, unit, px, py, ts, renderer):
        """Отрисовка радиуса обнаружения"""
        vision = unit.vision_range
        
        # Рисуем круг радиуса обнаружения
        center_x = px + ts // 2
        center_y = py + ts // 2
        radius = vision * ts
        
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (100, 200, 100, 20), (center_x, center_y), radius)
        pygame.draw.circle(overlay, (100, 200, 100, 60), (center_x, center_y), radius, 1)
        screen.blit(overlay, (0, 0))
