import random
import math
from . import config


class PerlinNoise:
    """Упрощенная реализация шума Перлина"""
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.permutation = list(range(256))
        random.shuffle(self.permutation)
        self.permutation *= 2
    
    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, t, a, b):
        return a + t * (b - a)
    
    def _grad(self, hash, x, y):
        h = hash & 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return (u if h & 1 == 0 else -u) + (v if h & 2 == 0 else -v)
    
    def noise(self, x, y):
        X = int(x) & 255
        Y = int(y) & 255
        
        x -= math.floor(x)
        y -= math.floor(y)
        
        u = self._fade(x)
        v = self._fade(y)
        
        A = self.permutation[X] + Y
        B = self.permutation[X + 1] + Y
        
        return self._lerp(v,
            self._lerp(u,
                self._grad(self.permutation[A], x, y),
                self._grad(self.permutation[B], x - 1, y)
            ),
            self._lerp(u,
                self._grad(self.permutation[A + 1], x, y - 1),
                self._grad(self.permutation[B + 1], x - 1, y - 1)
            )
        )
    
    def octave_noise(self, x, y, octaves, persistence):
        total = 0
        frequency = 1
        amplitude = 1
        max_value = 0
        
        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2
        
        return total / max_value


class Cell:
    def __init__(self, x, y, terrain_type):
        self.x = x
        self.y = y
        self.terrain = terrain_type
        self.units = []
        self.visible = False
        self.explored = False
        self.explored_player = False
        self.explored_enemy = False
        self.lasts_seen_enemy = None
        self.entrenchment = 0

    @property
    def color(self):
        return config.TERRAIN_COLORS[self.terrain]

    @property
    def name(self):
        return config.TERRAIN_NAMES[self.terrain]

    @property
    def is_walkable(self):
        return self.terrain != config.RIVER

    @property
    def defense_bonus(self):
        return config.TERRAIN_DEFENSE_BONUS[self.terrain]

    @property
    def cover_bonus(self):
        return config.TERRAIN_COVER_BONUS[self.terrain]


class GameMap:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height
        self.grid = [[None for _ in range(width)] for _ in range(height)]
        self.player_warehouse = None
        self.enemy_warehouses = []
        self._generate()

    def _generate(self):
        # Инициализация шума Перлина
        seed = random.randint(0, 1000000)
        perlin = PerlinNoise(seed)
        
        # Генерация базового рельефа с помощью шума
        for y in range(self.height):
            for x in range(self.width):
                # Многослойный шум для разнообразия
                elevation = perlin.octave_noise(x * 0.1, y * 0.1, 4, 0.5)
                moisture = perlin.octave_noise(x * 0.15 + 100, y * 0.15 + 100, 3, 0.6)
                
                # Определение типа местности на основе шума
                if elevation < -0.3:
                    terrain = config.RIVER
                elif elevation < -0.1:
                    terrain = config.FIELD
                elif moisture > 0.2:
                    terrain = config.FOREST
                else:
                    terrain = config.FIELD
                
                self.grid[y][x] = Cell(x, y, terrain)
        
        # Создание лесных массивов (вытянутых и разнообразной формы)
        forest_count = random.randint(3, 6)
        for _ in range(forest_count):
            # Случайная начальная точка
            start_x = random.randint(5, self.width - 5)
            start_y = random.randint(5, self.height - 5)
            
            # Случайное направление и длина
            direction = random.uniform(0, 2 * math.pi)
            length = random.randint(8, 15)
            
            # Создание вытянутого леса
            for i in range(length):
                x = int(start_x + i * math.cos(direction))
                y = int(start_y + i * math.sin(direction))
                
                # Добавляем случайное отклонение
                x += random.randint(-2, 2)
                y += random.randint(-2, 2)
                
                # Создаем кластер вокруг точки
                for dy in range(-3, 4):
                    for dx in range(-3, 4):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            # Шанс леса зависит от расстояния от центра
                            dist = math.sqrt(dx*dx + dy*dy)
                            if dist <= 3 and random.random() > dist * 0.2:
                                if self.grid[ny][nx].terrain != config.RIVER:
                                    self.grid[ny][nx].terrain = config.FOREST
                
                # Случайное изменение направления
                direction += random.uniform(-0.3, 0.3)
        
        # Создание полян в лесу
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x].terrain == config.FOREST:
                    # Шанс создать поляну
                    if random.random() < 0.05:
                        # Создаем поляну размером 2-4 клетки
                        size = random.randint(2, 4)
                        for dy in range(-size, size + 1):
                            for dx in range(-size, size + 1):
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < self.width and 0 <= ny < self.height:
                                    dist = math.sqrt(dx*dx + dy*dy)
                                    if dist <= size and random.random() > 0.3:
                                        self.grid[ny][nx].terrain = config.FIELD
        
        # Создание рек с поворотами
        river_count = random.randint(1, 3)
        for _ in range(river_count):
            # Начинаем с края карты
            if random.random() < 0.5:
                # Горизонтальная река
                x = 0
                y = random.randint(5, self.height - 5)
                direction = 0  # Вправо
                max_steps = self.width * 2
                
                for step in range(max_steps):
                    if x >= self.width:
                        break
                    
                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.grid[y][x].terrain = config.RIVER
                        # Ширина реки
                        if random.random() < 0.3:
                            if y + 1 < self.height:
                                self.grid[y + 1][x].terrain = config.RIVER
                    
                    # Повороты
                    if random.random() < 0.1:
                        direction += random.choice([-1, 1]) * random.uniform(0.3, 0.8)
                    
                    x += int(math.cos(direction))
                    y += int(math.sin(direction))
                    y = max(0, min(self.height - 1, y))
                    
                    # Если не движемся вперед, прерываем
                    if x <= step // 2:
                        break
            else:
                # Вертикальная река
                x = random.randint(5, self.width - 5)
                y = 0
                direction = math.pi / 2  # Вниз
                max_steps = self.height * 2
                
                for step in range(max_steps):
                    if y >= self.height:
                        break
                    
                    if 0 <= x < self.width and 0 <= y < self.height:
                        self.grid[y][x].terrain = config.RIVER
                        # Ширина реки
                        if random.random() < 0.3:
                            if x + 1 < self.width:
                                self.grid[y][x + 1].terrain = config.RIVER
                    
                    # Повороты
                    if random.random() < 0.1:
                        direction += random.choice([-1, 1]) * random.uniform(0.3, 0.8)
                    
                    x += int(math.cos(direction))
                    y += int(math.sin(direction))
                    x = max(0, min(self.width - 1, x))
                    
                    # Если не движемся вперед, прерываем
                    if y <= step // 2:
                        break
        
        # Создание населенных пунктов
        city_count = random.randint(4, 7)
        cities = []
        
        for _ in range(city_count):
            for attempt in range(50):
                cx = random.randint(5, self.width - 5)
                cy = random.randint(5, self.height - 5)
                
                if self.grid[cy][cx].terrain == config.RIVER:
                    continue
                
                too_close = False
                for other_x, other_y in cities:
                    if math.sqrt((cx - other_x)**2 + (cy - other_y)**2) < 12:
                        too_close = True
                        break
                
                if too_close:
                    continue
                
                cities.append((cx, cy))
                break
        
        # Соединяем города дорогами - каждый город с ближайшим
        connected = set()
        if cities:
            connected.add(0)
        
        # Алгоритм: соединяем ближайший несоединенный город к любому соединенному
        while len(connected) < len(cities):
            best_dist = float('inf')
            best_pair = None
            for i in connected:
                for j in range(len(cities)):
                    if j in connected:
                        continue
                    x1, y1 = cities[i]
                    x2, y2 = cities[j]
                    dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (i, j)
            
            if best_pair:
                i, j = best_pair
                x1, y1 = cities[i]
                x2, y2 = cities[j]
                self._create_road(x1, y1, x2, y2)
                connected.add(j)
            else:
                break
        
        # Дополнительно соединяем близкие города
        for i in range(len(cities)):
            for j in range(i + 1, len(cities)):
                x1, y1 = cities[i]
                x2, y2 = cities[j]
                dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                
                if dist < 25:
                    self._create_road(x1, y1, x2, y2)
        
        # Генерируем здания вдоль дорог в городе
        for cx, cy in cities:
            city_radius = random.randint(4, 6)
            
            # Ищем дороги в радиусе города
            road_cells = []
            for dy in range(-city_radius, city_radius + 1):
                for dx in range(-city_radius, city_radius + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if self.grid[ny][nx].terrain == config.ROAD:
                            road_cells.append((nx, ny))
            
            # Если дорог нет, создаем основные улицы
            if not road_cells:
                # Горизонтальная улица через центр
                for d in range(-city_radius, city_radius + 1):
                    rx = cx + d
                    if 0 <= rx < self.width and 0 <= cy < self.height:
                        if self.grid[cy][rx].terrain not in (config.RIVER, config.ROAD):
                            self.grid[cy][rx].terrain = config.ROAD
                            road_cells.append((rx, cy))
                
                # Вертикальная улица через центр
                for d in range(-city_radius, city_radius + 1):
                    ry = cy + d
                    if 0 <= cx < self.width and 0 <= ry < self.height:
                        if self.grid[ry][cx].terrain not in (config.RIVER, config.ROAD):
                            self.grid[ry][cx].terrain = config.ROAD
                            road_cells.append((cx, ry))
            
            # Кольцевая дорога для городов с радиусом >= 5
            if city_radius >= 5:
                ring_r = city_radius - 1
                # Верхняя и нижняя сторона
                for dx in range(-ring_r, ring_r + 1):
                    for ry_offset in [-ring_r, ring_r]:
                        rx, ry = cx + dx, cy + ry_offset
                        if 0 <= rx < self.width and 0 <= ry < self.height:
                            if self.grid[ry][rx].terrain not in (config.RIVER, config.ROAD, config.CITY):
                                self.grid[ry][rx].terrain = config.ROAD
                                road_cells.append((rx, ry))
                # Левая и правая сторона
                for dy in range(-ring_r, ring_r + 1):
                    for rx_offset in [-ring_r, ring_r]:
                        rx, ry = cx + rx_offset, cy + dy
                        if 0 <= rx < self.width and 0 <= ry < self.height:
                            if self.grid[ry][rx].terrain not in (config.RIVER, config.ROAD, config.CITY):
                                self.grid[ry][rx].terrain = config.ROAD
                                road_cells.append((rx, ry))
            
            # Тупиковые улицы
            if city_radius >= 4:
                # Тупики от горизонтальной улицы
                for sx in [cx - city_radius + 2, cx + city_radius - 2]:
                    dead_len = random.randint(2, 3)
                    dir_y = random.choice([-1, 1])
                    for d in range(1, dead_len + 1):
                        dy = cy + dir_y * d
                        if 0 <= sx < self.width and 0 <= dy < self.height:
                            if self.grid[dy][sx].terrain not in (config.RIVER, config.ROAD):
                                self.grid[dy][sx].terrain = config.ROAD
                                road_cells.append((sx, dy))
                
                # Тупики от вертикальной улицы
                for sy in [cy - city_radius + 2, cy + city_radius - 2]:
                    dead_len = random.randint(2, 3)
                    dir_x = random.choice([-1, 1])
                    for d in range(1, dead_len + 1):
                        dx = cx + dir_x * d
                        if 0 <= dx < self.width and 0 <= sy < self.height:
                            if self.grid[sy][dx].terrain not in (config.RIVER, config.ROAD):
                                self.grid[sy][dx].terrain = config.ROAD
                                road_cells.append((dx, sy))
            
            # Размещаем здания (CITY) рядом с дорогами
            build_radius = city_radius + 2 if city_radius >= 5 else city_radius
            for rx, ry in road_cells:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                    bx, by = rx + dx, ry + dy
                    if 0 <= bx < self.width and 0 <= by < self.height:
                        if self.grid[by][bx].terrain == config.FIELD:
                            dist_to_center = math.sqrt((bx - cx)**2 + (by - cy)**2)
                            if dist_to_center <= build_radius and random.random() < 0.6:
                                self.grid[by][bx].terrain = config.CITY
            
            # Центр города - здание если не дорога и не река
            if 0 <= cx < self.width and 0 <= cy < self.height:
                if self.grid[cy][cx].terrain not in (config.RIVER, config.ROAD):
                    self.grid[cy][cx].terrain = config.CITY
        
        # Размещение складов в городах
        # База игрока - ищем клетку здания рядом с центром
        player_city = cities[0] if cities else (3, self.height // 2)
        px, py = player_city
        wh_placed = False
        for r in range(4):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    wx, wy = px + dx, py + dy
                    if 0 <= wx < self.width and 0 <= wy < self.height:
                        if self.grid[wy][wx].terrain == config.CITY:
                            player_city = (wx, wy)
                            wh_placed = True
                            break
                if wh_placed:
                    break
            if wh_placed:
                break
        self.player_warehouse = player_city
        
        # Базы врага
        if len(cities) >= 2:
            enemy_cities = [cities[1]]
        else:
            enemy_cities = [(self.width - 4, self.height // 2)]
            for ex, ey in enemy_cities:
                for r in range(4):
                    found = False
                    for dx in range(-r, r + 1):
                        for dy in range(-r, r + 1):
                            wx, wy = ex + dx, ey + dy
                            if 0 <= wx < self.width and 0 <= wy < self.height:
                                if self.grid[wy][wx].terrain == config.CITY:
                                    enemy_cities[enemy_cities.index((ex, ey))] = (wx, wy)
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break
        
        self.enemy_warehouses = enemy_cities
    
    def _create_road(self, x1, y1, x2, y2):
        """Создать дорогу между двумя точками, избегая воды"""
        x, y = x1, y1
        
        # Двигаемся по X
        while x != x2:
            if 0 <= x < self.width and 0 <= y < self.height:
                terrain = self.grid[y][x].terrain
                if terrain == config.RIVER:
                    # Обход реки: сдвигаемся вверх или вниз
                    for try_dy in [-1, 1, -2, 2]:
                        ny = y + try_dy
                        if 0 <= ny < self.height and self.grid[ny][x].terrain != config.RIVER:
                            # Прокладываем обходную дорогу
                            for step in range(abs(try_dy)):
                                sy = y + (1 if try_dy > 0 else -1) * step
                                if 0 <= sy < self.height and self.grid[sy][x].terrain in (config.FIELD, config.FOREST):
                                    self.grid[sy][x].terrain = config.ROAD
                            y = ny
                            break
                elif terrain in (config.FIELD, config.FOREST):
                    self.grid[y][x].terrain = config.ROAD
            x += 1 if x2 > x else -1
        
        # Двигаемся по Y
        while y != y2:
            if 0 <= x < self.width and 0 <= y < self.height:
                terrain = self.grid[y][x].terrain
                if terrain == config.RIVER:
                    # Обход реки: сдвигаемся влево или вправо
                    for try_dx in [-1, 1, -2, 2]:
                        nx = x + try_dx
                        if 0 <= nx < self.width and self.grid[y][nx].terrain != config.RIVER:
                            for step in range(abs(try_dx)):
                                sx = x + (1 if try_dx > 0 else -1) * step
                                if 0 <= sx < self.width and self.grid[y][sx].terrain in (config.FIELD, config.FOREST):
                                    self.grid[y][sx].terrain = config.ROAD
                            x = nx
                            break
                elif terrain in (config.FIELD, config.FOREST):
                    self.grid[y][x].terrain = config.ROAD
            y += 1 if y2 > y else -1

    def get_cell(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return None

    def is_valid(self, x, y):
        cell = self.get_cell(x, y)
        return cell is not None and cell.is_walkable

    def get_neighbors(self, x, y, include_impassable=False, unit=None):
        can_fly = unit is not None and getattr(unit, 'is_flying', False)
        neighbors = []
        for dx, dy in config.DIRECTIONS:
            nx, ny = x + dx, y + dy
            cell = self.get_cell(nx, ny)
            if not cell:
                continue
            if include_impassable or cell.is_walkable or can_fly:
                neighbors.append((nx, ny))
        return neighbors

    def distance(self, x1, y1, x2, y2):
        return abs(x1 - x2) + abs(y1 - y2)

    def remove_unit(self, unit):
        for y in range(self.height):
            for x in range(self.width):
                if unit in self.grid[y][x].units:
                    self.grid[y][x].units.remove(unit)
                    return

    def add_unit(self, unit, x, y):
        cell = self.get_cell(x, y)
        if cell:
            cell.units.append(unit)
            unit.x, unit.y = x, y

    def get_units_at(self, x, y, faction=None):
        cell = self.get_cell(x, y)
        if not cell:
            return []
        if faction is None:
            return cell.units[:]
        return [u for u in cell.units if u.faction == faction]

    def _has_los(self, x1, y1, x2, y2):
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        cx, cy = x1, y1
        while True:
            if cx == x2 and cy == y2:
                return True
            if (cx != x1 or cy != y1) and (cx != x2 or cy != y2):
                cell = self.get_cell(cx, cy)
                if cell and cell.terrain in (config.FOREST, config.CITY):
                    return False
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    def _detection_range(self, observer, target_stealth):
        return max(0, observer.vision_range - target_stealth)

    @staticmethod
    def _get_stealth(unit, game_map=None):
        bonus = 0
        if game_map:
            cell = game_map.get_cell(unit.x, unit.y)
            bonus += cell.entrenchment // 40  # 0-2
        if hasattr(unit, 'supplies') and not hasattr(unit, 'soldiers'):
            bonus += 4  # warehouses are well camouflaged
        return bonus

    @staticmethod
    def _cell_stealth_bonus(terrain):
        if terrain == config.FOREST:
            return 2
        if terrain == config.CITY:
            return 1
        return 0

    def update_visibility(self, units, all_units=None, faction=None):
        for y in range(self.height):
            for x in range(self.width):
                self.grid[y][x].visible = False

        for unit in units:
            if not unit.is_alive:
                continue
            if hasattr(unit, 'jammed') and unit.jammed:
                continue
            vision = unit.vision_range
            for dy in range(-vision, vision + 1):
                for dx in range(-vision, vision + 1):
                    nx, ny = unit.x + dx, unit.y + dy
                    cell = self.get_cell(nx, ny)
                    if cell is None:
                        continue
                    dist = abs(dx) + abs(dy)
                    if dist > vision:
                        continue
                    if not self._has_los(unit.x, unit.y, nx, ny):
                        continue
                    cell.visible = True
                    cell.explored = True
                    # Update faction-specific explored flag
                    if faction is not None:
                        if faction == config.PLAYER:
                            cell.explored_player = True
                        elif faction == config.ENEMY:
                            cell.explored_enemy = True

    def find_path(self, start_x, start_y, end_x, end_y, max_cost=None, unit=None, avoid_units=None, avoid_occupied=False):
        import heapq
        if not self.is_valid(end_x, end_y) and not (unit and getattr(unit, 'is_flying', False)):
            return None
        visited = {}
        # Приоритетная очередь: (cost, x, y)
        q = [(0, start_x, start_y)]
        visited[(start_x, start_y)] = (None, 0)
        
        while q:
            cost, x, y = heapq.heappop(q)
            
            if (x, y) == (end_x, end_y):
                path = []
                cur = (end_x, end_y)
                while cur:
                    path.append(cur)
                    cur = visited[cur][0]
                path.reverse()
                return path
            
            # Если уже нашли более дешёвый путь к этой клетке
            if (x, y) in visited and visited[(x, y)][1] < cost:
                continue
                
            if max_cost is not None and cost >= max_cost:
                continue
                
            for nx, ny in self.get_neighbors(x, y, unit=unit):
                # Skip cells occupied by explicitly listed units
                if avoid_units:
                    blocked = False
                    for u in avoid_units:
                        if u.x == nx and u.y == ny and u.is_alive:
                            blocked = True
                            break
                    if blocked:
                        continue
                # Skip cells occupied by any living unit on the map
                if avoid_occupied:
                    cell = self.get_cell(nx, ny)
                    if cell and any(u.is_alive for u in cell.units):
                        continue
                
                move_cost = 1
                if unit and hasattr(unit, 'get_movement_cost'):
                    move_cost = unit.get_movement_cost(self.get_cell(nx, ny).terrain)
                
                new_cost = cost + move_cost
                
                if max_cost is not None and new_cost > max_cost:
                    continue
                
                if (nx, ny) not in visited or visited[(nx, ny)][1] > new_cost:
                    visited[(nx, ny)] = ((x, y), new_cost)
                    heapq.heappush(q, (new_cost, nx, ny))
        
        return None

    def serialize(self):
        """Сериализовать карту для сохранения игры"""
        cells = []
        for row in self.grid:
            for cell in row:
                cells.append({
                    'x': cell.x,
                    'y': cell.y,
                    'terrain': cell.terrain,
                    'entrenchment': cell.entrenchment,
                    'visible': cell.visible,
                    'explored': cell.explored,
                    'explored_player': cell.explored_player,
                    'explored_enemy': cell.explored_enemy,
                    'lasts_seen_enemy': cell.lasts_seen_enemy,
                })
        return {
            'width': self.width,
            'height': self.height,
            'player_warehouse': self.player_warehouse,
            'enemy_warehouses': self.enemy_warehouses,
            'cells': cells,
        }

    @classmethod
    def restore(cls, data):
        """Восстановить карту из сериализованных данных"""
        gm = cls.__new__(cls)
        gm.width = data['width']
        gm.height = data['height']
        gm.grid = [[None for _ in range(gm.width)] for _ in range(gm.height)]
        gm.player_warehouse = data.get('player_warehouse')
        gm.enemy_warehouses = data.get('enemy_warehouses', [])
        for c in data['cells']:
            cell = Cell(c['x'], c['y'], c['terrain'])
            cell.entrenchment = c.get('entrenchment', 0)
            cell.visible = c.get('visible', False)
            cell.explored = c.get('explored', False)
            cell.explored_player = c.get('explored_player', False)
            cell.explored_enemy = c.get('explored_enemy', False)
            cell.lasts_seen_enemy = c.get('lasts_seen_enemy')
            gm.grid[c['y']][c['x']] = cell
        return gm

    def get_reachable_cells(self, start_x, start_y, max_cost, unit=None, max_steps=None):
        reachable = set()
        visited = {}
        queue = [(start_x, start_y, 0, 0)]  # (x, y, cost, steps)
        visited[(start_x, start_y)] = (0, 0)

        while queue:
            x, y, cost, steps = queue.pop(0)
            if cost > max_cost:
                continue
            if max_steps is not None and steps > max_steps:
                continue
            if not self.is_valid(x, y):
                continue
            reachable.add((x, y))

            for nx, ny in self.get_neighbors(x, y, unit=unit):
                move_cost = 1
                if unit and hasattr(unit, 'get_movement_cost'):
                    move_cost = unit.get_movement_cost(self.get_cell(nx, ny).terrain)
                new_cost = cost + move_cost
                new_steps = steps + 1
                if (nx, ny) not in visited or visited[(nx, ny)][0] > new_cost:
                    visited[(nx, ny)] = (new_cost, new_steps)
                    if new_cost <= max_cost and (max_steps is None or new_steps <= max_steps):
                        queue.append((nx, ny, new_cost, new_steps))

        reachable.discard((start_x, start_y))
        return reachable
