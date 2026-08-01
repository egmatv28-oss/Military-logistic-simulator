# PROJECT MAP — Военная Логистика

> Пошаговый военный симулятор с акцентом на логистику снабжения.
> Python 3.12 + Pygame 2.6.1. Без внешних зависимостей, кроме pygame.

---

## 1. Как запустить

```
cd military_logistics_sim
pip install pygame
python main.py
```

---

## 2. Полная карта файлов

```
military_logistics_sim/
│
├── main.py                        ← Точка входа. Создаёт окно, меню, игровой цикл.
│
├── game/
│   ├── __init__.py                ← Реэкспорт: from game import Game
│   │
│   ├── game_config.py             ← ВСЕ константы: экран, цвета, типы местности,
│   │                                  параметры юнитов, фазы, грузы, фракции.
│   │
│   ├── game.py                    ← ФАСАД: __init__ (состояние), _setup (расстановка),
│   │                                  свойства + делегирование менеджерам.
│   │
│   ├── units.py                   ← ВСЕ классы юнитов: Soldier, Infantry, Tank,
│   │                                  Artillery, ReconDrone, FPVDrone, FPVOperator,
│   │                                  ReconOperator, SupplyTruck, SupplyCache,
│   │                                  SoldierUnit, Warehouse, RadarEW.
│   │
│   ├── map_.py                    ← Карта: PerlinNoise, Cell, GameMap.
│   │                                  Генерация, поиск пути (BFS), видимость.
│   │
│   ├── combat.py                  ← Боевая система: resolve_attack, resolve_fpv_strike.
│   │                                  Пехота vs пехота, танк vs танк, артиллерия, FPV.
│   │
│   ├── resource_transfer.py       ← Передача ресурсов между юнитами.
│   │                                  Диспетчер (source_type, target_type) → handler.
│   │
│   ├── turn_manager.py            ← Менеджер хода: фазы, конец хода, подкрепления,
│   │                                  hot-seat, боевые эффекты, автоатака.
│   │
│   ├── action_manager.py          ← Команды игрока: движение, атака, окапывание,
│   │                                  строительство, передача ресурсов, управление составом.
│   │
│   ├── supply_logistics.py        ← Логистика: маршруты грузовиков, waypoints,
│   │                                  загрузка/разгрузка, передача со складов/погребов.
│   │
│   ├── unit_animation.py          ← Анимация пошагового движения юнитов.
│   │
│   ├── ai.py                      ← Устаревший AI-контроллер (обёртка над StrategicAI).
│   │
│   ├── strategic_ai.py            ← Стратегический ИИ: разведка → логистика → атака.
│   │
│   ├── renderer.py                ← ФАСАД рендера: __init__, render(), камера/зум.
│   │
│   ├── ui_manager.py              ← Обработка ввода (клавиатура + мышь),
│   │                                  делегирование в Game, чит-консоль.
│   │
│   ├── controllers/
│   │   ├── __init__.py            ← Реэкспорт: BaseController, AIController, HumanController
│   │   ├── base_controller.py     ← Абстрактный BaseController (интерфейс).
│   │   ├── ai_controller.py       ← AIController: ход ИИ через StrategicAI.
│   │   └── human_controller.py    ← HumanController: ход человека (hot-seat).
│   │
│   ├── renderers/
│   │   ├── __init__.py            ← Реэкспорт всех 5 рендереров.
│   │   ├── map_renderer.py        ← Отрисовка карты: тайлы, туман, дороги, пути, waypoints.
│   │   ├── unit_renderer.py       ← Отрисовка юнитов: все типы, HP-бары, индикаторы.
│   │   ├── ui_panel_renderer.py   ← Панель справа: ресурсы, кнопки, состав, журнал.
│   │   ├── effects_renderer.py    ← Эффекты: взрывы, рикошеты, подсветка передачи.
│   │   └── esp_renderer.py        ← ESP: консоль читов, hot-seat экран.
│   │
│   ├── ui/
│   │   ├── __init__.py            ← Реэкспорт: Menu, LoadGameMenu, ESPMenu
│   │   ├── menu.py                ← Главное меню и меню загрузки.
│   │   └── esp_menu.py            ← ESP-меню: читы, оверлеи, состав, сохранение.
│   │
│   ├── config/
│   │   ├── __init__.py            ← Реэкспорт config_loader.
│   │   ├── config_loader.py       ← Загрузчик JSON-конфигураций (пока не используется).
│   │   └── unit_configs/
│   │       └── units.json         ← JSON-конфигурация юнитов (пока не используется).
│   │
│   └── utils/
│       ├── __init__.py            ← Реэкспорт: SaveLoadSystem
│       └── save_load.py           ← Сохранение/загрузка через pickle.
│
├── saves/                         ← Папка с сохранениями (.sav файлы).
│
├── start_game.bat                 ← Скрипт запуска для Windows.
│
└── test_*.py                      ← Тестовые скрипты.
```

---

## 3. Как работает архитектура

### 3.1 Паттерн «Фасад + Менеджеры»

Главный класс `Game` (game.py) — это **фасад**. Он:
1. Хранит **всё состояние** (юниты, карта, фаза, waypoints, UI-флаги).
2. Создаёт 4 менеджера в `__init__`.
3. Делегирует им через однострочные методы-прокладки.

```
Game (571 строка — фасад)
 ├── _turn_mgr  → TurnManager    (887 строк — логика хода)
 ├── _action_mgr → ActionManager (754 строк — команды игрока)
 ├── _supply_mgr → SupplyLogistics (811 строк — логистика)
 └── _anim_mgr   → UnitAnimation  (62 строки — анимация)
```

**Почему так?** Менеджеры не хранят своё состояние — всё живёт в `Game`.
Менеджеры получают `self.game` и обращаются к состоянию через него.
Это упрощает сериализацию (save/load) и убирает циклические зависимости.

### 3.2 Паттерн «Фасад + Суб-рендереры»

Аналогично, `Renderer` (renderer.py) — фасад для отрисовки:

```
Renderer (129 строк — фасад)
 ├── _map     → MapRenderer        (520 строк)
 ├── _units   → UnitRenderer       (574 строки)
 ├── _panel   → UIPanelRenderer    (1210 строк)
 ├── _effects → EffectsRenderer    (359 строк)
 └── _esp     → ESPRenderer        (55 строк)
```

Суб-рендереры получают `self.r` (ссылку на главный Renderer)
и обращаются к `self.r.screen`, `self.r.font_*`, `self.r.camera_*`, `self.r.tsize`.

### 3.3 Поток данных (один ход)

```
main.py: pygame event loop
  → ui_manager.handle_event()        ← обработка кликов/клавиш
    → game.order_attack()            ← делегирует в ActionManager
      → combat.resolve_attack()      ← вычисление урона
  → game.update()                    ← делегирует в TurnManager
    → TurnManager.advance_phase()    ← движение → обнаружение → бой → логистика → конец хода
  → renderer.render(game)            ← делегирует суб-рендерерам
    → MapRenderer._draw_map()
    → UnitRenderer._draw_units()
    → UIPanelRenderer._draw_right_panel()
```

---

## 4. Граф зависимостей (кто импортирует кого)

```
main.py
├── game.Game
├── game.renderer.Renderer
├── game.ui_manager.UIManager
├── game.ui.menu.Menu, LoadGameMenu
├── game.utils.save_load.SaveLoadSystem
└── game.config

game.Game
├── game.config
├── game.map_.GameMap
├── game.units.*
├── game.combat.resolve_attack
├── game.controllers.AIController, HumanController
├── game.resource_transfer (implicit via managers)
├── game.turn_manager.TurnManager
├── game.action_manager.ActionManager
├── game.supply_logistics.SupplyLogistics
└── game.unit_animation.UnitAnimation

game.turn_manager
├── game.config
├── game.units.*
└── game.combat.resolve_attack

game.action_manager
├── game.config
├── game.units.*
├── game.combat.resolve_attack, resolve_fpv_strike
└── game.resource_transfer.transfer, can_accept_resource

game.supply_logistics
├── game.config
├── game.units.*
└── game.resource_transfer.transfer, can_accept_resource

game.resource_transfer
├── game.config
└── game.units.*

game.renderer
├── game.config
└── game.renderers.* (MapRenderer, UnitRenderer, ...)

game.renderers.*
├── game.config
└── game.units.*

game.ui_manager
├── game.config
├── game.units.*
├── game.utils.save_load.SaveLoadSystem
└── game.ui.esp_menu.ESPMenu

game.strategic_ai
├── game.config
└── game.units.*

game.controllers.ai_controller
├── game.config
├── game.units.*
└── game.strategic_ai.StrategicAI
```

---

## 5. Самые важные функции

### game.py — состояние и фасад
| Что | Строка | Зачем |
|---|---|---|
| `Game.__init__` | 10 | Инициализация ВСЕГО состояния (60+ полей) + создание менеджеров |
| `Game._setup` | 104 | Расстановка начальных юнитов на карте |
| `Game.get_unit_max_move` | 356 | Очки движения юнита (используется везде) |
| `Game._add_resource_transfer_effect` | 383 | Визуальный эффект передачи ресурсов |

### units.py — модель юнитов
| Что | Строка | Зачем |
|---|---|---|
| `Soldier` | 68 | Модель солдата: имя, здоровье, навыки, ранения, еда, боеприпасы |
| `Infantry` | 302 | Пехотное подразделение (список солдат, укрепление) |
| `Tank` | 746 | Танк (экипаж, броня, топливо, снаряды) |
| `Artillery` | 893 | Артиллерия (дальний бой) |
| `SupplyTruck` | 1366 | Грузовик (груз, маршрут, экипаж) |
| `Warehouse` | (далее) | Склад (ресурсы, пополнение) |
| `SupplyCache` | (далее) | Погреб (строящееся/построенное сооружение) |
| `RadarEW` | 1139 | Радиоэлектронная борьба (РЭБ) |

### map_.py — карта и навигация
| Что | Строка | Зачем |
|---|---|---|
| `GameMap._generate` | 109 | Процедурная генерация (шум Перлина, леса, реки, города, дороги) |
| `GameMap.find_path` | 459 | BFS поиск пути с учётом стоимости местности |
| `GameMap.update_visibility` | 430 | Обновление тумана войны |

### combat.py — боевая система
| Что | Строка | Зачем |
|---|---|---|
| `resolve_attack` | 14 | Диспетчер атак по типам юнитов |
| `resolve_infantry_vs_infantry` | 34 | Перестрелка с контратакой |
| `resolve_tank_vs_tank` | 143 | Танковый дуэль с рикошетами |

### turn_manager.py — логика хода
| Что | Строка | Зачем |
|---|---|---|
| `TurnManager.advance_phase` | 33 | Переключение фаз: движение → обнаружение → бой → логистика → конец |
| `TurnManager.end_turn` | 238 | Конец хода: голод, подкрепления, очистка мёртвых |
| `TurnManager._auto_attack_adjacent` | 60 | Автоматическая атака при соприкосновении |

### resource_transfer.py — передача ресурсов
| Что | Строка | Зачем |
|---|---|---|
| `transfer(source, target, res_type)` | 624 | Единая точка входа для передачи любого ресурса |
| `_TRANSFER_TABLE` | 405 | Словарь-диспетчер (source_type, target_type) → handler |
| `_soldiers_give_to_soldiers` | 10 | Универсальная передача food/ammo между солдатами |

---

## 6. Как добавить НОВЫЙ ТИП ЮНИТА

### Шаг 1. Добавить константы в `game_config.py`

```python
# Добавить тип
NEW_UNIT = "new_unit"

# Добавить параметры
NEW_UNIT_MAX_HP = 100
NEW_UNIT_MOVE_POINTS = 5
NEW_UNIT_STEPS_PER_TURN = 2
```

### Шаг 2. Создать класс в `units.py`

```python
class NewUnit(Unit):
    def __init__(self, x, y, faction, name="Новый юнит"):
        super().__init__(x, y, config.NEW_UNIT, faction, name)
        self.hp = config.NEW_UNIT_MAX_HP
        self.color = (100, 200, 100) if faction == config.PLAYER else (200, 100, 100)

    def status_lines(self):
        return [f"HP: {self.hp}/{config.NEW_UNIT_MAX_HP}"]

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.die()
```

### Шаг 3. Добавить в `game.py` → `_setup()` размещение на карте

```python
new_unit = NewUnit(wx + 2, wy + 2, config.PLAYER, "Мой юнит")
self.all_units.append(new_unit)
self.player_units.append(new_unit)
self.map.add_unit(new_unit, wx + 2, wy + 2)
```

### Шаг 4. Добавить отрисовку в `renderers/unit_renderer.py`

```python
# В _draw_units добавить ветку:
elif isinstance(unit, NewUnit):
    self._draw_new_unit(px, py, unit, game)

# Добавить метод:
def _draw_new_unit(self, px, py, unit, game):
    ts = self.r.tsize
    pygame.draw.rect(self.r.screen, unit.color, (px+2, py+2, ts-4, ts-4))
```

### Шаг 5. Добавить в `renderers/ui_panel_renderer.py` кнопки (опционально)

В `_draw_action_buttons` добавить ветку:
```python
elif isinstance(unit, NewUnit):
    buttons.append(("⚡", "Специальное действие", "new_action"))
```

### Шаг 6. Обработать действие в `action_manager.py` (опционально)

```python
# В Game или ActionManager добавить метод:
def order_new_action(self):
    unit = self.game.selected_unit
    # ... логика
```

### Шаг 7. Добавить в `game_config.py` → `VISION_RANGE` (если нужно)

```python
VISION_RANGE = {
    ...
    "new_unit": 3,
}
```

### Шаг 8. Добавить в `game.py` → `get_unit_max_move` / `get_unit_max_steps`

```python
elif isinstance(unit, NewUnit):
    return config.NEW_UNIT_MOVE_POINTS
```

### Шаг 9. Добавить в `save_load.py` → `unit_classes` (для сохранений)

```python
from ..units import ..., NewUnit
unit_classes = {
    ...
    'NewUnit': NewUnit,
}
```

---

## 7. Как добавить НОВУЮ ФАЗУ ХОДА

### Шаг 1. Добавить константу в `game_config.py`

```python
PHASE_NEW_PHASE = 8
PHASE_NAMES[PHASE_NEW_PHASE] = "Новая фаза"
```

### Шаг 2. Добавить метод в `turn_manager.py`

```python
def _do_new_phase(self):
    g = self.game
    # логика новой фазы
```

### Шаг 3. Встроить в `TurnManager.advance_phase()`

```python
elif g.phase == config.PHASE_ENTRENCH:
    self._do_entrench_phase()
    g.phase = config.PHASE_NEW_PHASE        # ← новая фаза
elif g.phase == config.PHASE_NEW_PHASE:      # ← обработка
    self._do_new_phase()
    g.phase = config.PHASE_ENEMY_TURN
```

---

## 8. Как добавить НОВУЮ КОМАНДУ ИГРОКА

### Шаг 1. Добавить метод в `action_manager.py`

```python
def order_my_command(self):
    g = self.game
    unit = g.selected_unit
    if not unit or not unit.is_alive:
        g.message = "Выберите юнит"
        return
    # ... логика
    g.message = "Команда выполнена"
```

### Шаг 2. Добавить делегат в `game.py`

```python
def order_my_command(self):
    self._action_mgr.order_my_command()
```

### Шаг 3. Добавить кнопку в `renderers/ui_panel_renderer.py`

В `_draw_action_buttons`:
```python
buttons.append(("🔧", "Моя команда", "my_command"))
```

### Шаг 4. Обработать клик в `ui_manager.py`

В `_handle_button_click`:
```python
elif action == "my_command":
    self.game.order_my_command()
```

Или через клавишу в `_handle_key`:
```python
elif key == pygame.K_z:
    self.game.order_my_command()
```

---

## 9. Как добавить НОВЫЙ РЕСУРС

### Шаг 1. Добавить константы в `game_config.py`

```python
CARGO_MEDKITS = "medkits"
CARGO_NAMES[CARGO_MEDKITS] = "Медкейты"
CARGO_WEIGHT_PER_UNIT[CARGO_MEDKITS] = 2
```

### Шаг 2. Добавить поле в нужные юниты (`units.py`)

```python
class Warehouse:
    def __init__(self, ...):
        ...
        self.medkits = 0
        self.max_medkits = 50
```

### Шаг 3. Добавить handler в `resource_transfer.py`

```python
def _warehouse_to_infantry_medkits(src, tgt, res_type, limit):
    if res_type != "medkits":
        return 0
    # ... логика передачи
```

Добавить в `_TRANSFER_TABLE`:
```python
(Warehouse, Infantry): _warehouse_to_infantry_with_medkits,  # заменить старый handler
```

### Шаг 4. Добавить отображение в `renderers/ui_panel_renderer.py`

В `_draw_resource_buttons`:
```python
resources.append(("💊", "Медкейты", unit.medkits, unit.max_medkits, "medkits"))
```

---

## 10. Как добавить НОВЫЙ РЕНДЕРЕР

### Шаг 1. Создать файл `game/renderers/my_renderer.py`

```python
import pygame
from .. import config

class MyRenderer:
    def __init__(self, renderer):
        self.r = renderer

    def draw_my_stuff(self, game):
        # self.r.screen, self.r.font_small, self.r.tsize, self.r.camera_x ...
        pass
```

### Шаг 2. Импортировать в `game/renderers/__init__.py`

```python
from .my_renderer import MyRenderer
```

### Шаг 3. Создать экземпляр в `game/renderer.py` → `__init__`

```python
from .renderers.my_renderer import MyRenderer
# В __init__:
self._my = MyRenderer(self)
```

### Шаг 4. Вызвать в `Renderer.render()`

```python
def render(self, game):
    ...
    self._my.draw_my_stuff(game)
    ...
```

---

## 11. Как добавить НОВЫЙ МЕНЕДЖЕР

### Шаг 1. Создать файл `game/my_manager.py`

```python
from . import config
from .units import Infantry, Tank  # нужные типы

class MyManager:
    def __init__(self, game):
        self.game = game

    def do_something(self):
        g = self.game
        # обращение к состоянию: g.all_units, g.map, g.message ...
```

### Шаг 2. Импортировать и создать в `game/game.py`

```python
from .my_manager import MyManager

class Game:
    def __init__(self, ...):
        ...
        self._my_mgr = MyManager(self)

    def do_something(self):          # ← делегат
        self._my_mgr.do_something()
```

---

## 12. Ключевые файлы и их размеры

| Файл | Строк | Роль |
|---|---|---|
| `game.py` | 511 | Фасад: состояние + делегирование |
| `turn_manager.py` | 958 | Логика хода, фазы, подкрепления |
| `supply_logistics.py` | 789 | Маршруты, склады, waypoints |
| `action_manager.py` | 824 | Команды игрока |
| `resource_transfer.py` | 578 | Передача ресурсов (диспетчер) |
| `units.py` | 1900 | Все классы юнитов |
| `ui_manager.py` | 873 | Обработка ввода |
| `map_.py` | 662 | Карта, путь, видимость |
| `combat.py` | 496 | Боевая система |
| `strategic_ai.py` | 845 | Стратегический ИИ |
| `renderer.py` | 111 | Фасад рендера |
| `ui_panel_renderer.py` | 1194 | Панель UI |
| `unit_renderer.py` | 733 | Отрисовка юнитов |
| `map_renderer.py` | 588 | Отрисовка карты |
| `esp_menu.py` | 572 | ESP-меню |
| `game_config.py` | 700+ | Все константы (200+ параметров балансировки) |
| **TOTAL** | **~13500** | |

---

## 13. Тестовые файлы

| Файл | Что тестирует |
|---|---|
| `test_cheat.py` | Чит-коды |
| `test_changes.py` | Изменения в коде |
| `test_full.py` | Полный сценарий |
| `test_load.py` | Загрузка сохранений |
| `test_movement.py` | Система движения |
| `test_truck.py` | Грузовики |

Запуск: `python test_full.py`
