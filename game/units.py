from . import config
import random

# Система ранений
WOUND_NONE = 0
WOUND_LIGHT = 1    # Лёгкое ранение - небольшой штраф
WOUND_MEDIUM = 2   # Среднее ранение - значительный штраф
WOUND_HEAVY = 3    # Тяжёлое ранение - критический штраф, нужна эвакуация

WOUND_NAMES = {
    WOUND_NONE: "Здоров",
    WOUND_LIGHT: "Лёгкое ранение",
    WOUND_MEDIUM: "Среднее ранение",
    WOUND_HEAVY: "Тяжёлое ранение",
}

WOUND_PENALTIES = {
    WOUND_NONE: {"attack": 0, "move": 0, "morale": 0},
    WOUND_LIGHT: {"attack": -10, "move": 0, "morale": -5},
    WOUND_MEDIUM: {"attack": -25, "move": -1, "morale": -15},
    WOUND_HEAVY: {"attack": -50, "move": -2, "morale": -30},
}

FIRST_NAMES_MALE = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
    "Никита", "Матвей", "Роман", "Егор", "Арсений", "Иван", "Даниил", "Тимофей", "Владислав", "Николай",
    "Павел", "Станислав", "Константин", "Евгений", "Денис", "Олег", "Виктор", "Антон", "Глеб", "Фёдор",
    "Руслан", "Захар", "Семён", "Ярослав", "Вадим", "Анатолий", "Игорь", "Валерий", "Сергей", "Георгий",
]

FIRST_NAMES_FEMALE = [
    "Александра", "Дарья", "Анна", "Мария", "Елена", "Ольга", "Наталья", "Анастасия", "Татьяна", "Ирина",
    "Светлана", "Екатерина", "Юлия", "Марина", "Вероника", "Полина", "Ксения", "Виктория", "Алина", "Валерия",
    "Алиса", "Милана", "Ева", "Амелия", "София", "Виолетта", "Маргарита", "Кристина", "Елизавета", "Ангелина",
    "Василиса", "Ульяна", "Платоновна", "Злата", "Мия", "Эвелина", "Агата", "Авигея", "Авигея", "Аврора",
]

SURNAMES_MALE = [
    "Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков", "Фёдоров",
    "Морозов", "Волков", "Алексеев", "Лебедев", "Семёнов", "Егоров", "Павлов", "Козлов", "Степанов", "Николаев",
    "Орлов", "Андреев", "Макаров", "Никитин", "Захаров", "Зайцев", "Соловьёв", "Борисов", "Яковлев", "Григорьев",
    "Романов", "Воробьёв", "Сергеев", "Кузьмин", "Фролов", "Александров", "Дмитриев", "Королёв", "Гусев", "Киселёв",
    "Ильин", "Максимов", "Поляков", "Сорокин", "Виноградов", "Ковалёв", "Белов", "Медведев", "Антонов", "Тарасов",
]

SURNAMES_FEMALE = [
    "Иванова", "Смирнова", "Кузнецова", "Попова", "Васильева", "Петрова", "Соколова", "Михайлова", "Новикова", "Фёдорова",
    "Морозова", "Волкова", "Алексеева", "Лебедева", "Семёнова", "Егорова", "Павлова", "Козлова", "Степанова", "Николаева",
    "Орлова", "Андреева", "Макарова", "Никитина", "Захарова", "Зайцева", "Соловьёва", "Борисова", "Яковлева", "Григорьева",
    "Романова", "Воробьёва", "Сергеева", "Кузьмина", "Фролова", "Александрова", "Дмитриева", "Королёва", "Гусева", "Киселёва",
    "Ильина", "Максимова", "Полякова", "Сорокина", "Виноградова", "Ковалёва", "Белова", "Медведева", "Антонова", "Тарасова",
]

SKILLS = [
    "Стрельба",
    "Тактика",
    "Выносливость",
    "Маскировка",
    "Медицина",
    "Инженерное дело",
    "Радиосвязь",
    "Вождение",
    "Лидерство",
    "Навигация",
]


class Soldier:
    _global_dead_count = 0

    def __init__(self, name=None, surname=None, gender=None, skills=None, role=None):
        self.gender = gender or random.choice(["male", "female"])
        self.role = role or "Солдат"
        
        if self.gender == "male":
            self.name = name or random.choice(FIRST_NAMES_MALE)
            self.surname = surname or random.choice(SURNAMES_MALE)
        else:
            self.name = name or random.choice(FIRST_NAMES_FEMALE)
            self.surname = surname or random.choice(SURNAMES_FEMALE)
        
        if skills is None:
            num_skills = random.randint(2, 4)
            self.skills = random.sample(SKILLS, num_skills)
        else:
            self.skills = skills
        
        self.experience = random.randint(0, 20)
        self.morale = random.randint(50, 100)
        self.health = 100
        self._is_alive = True
        self.food = config.SOLDIER_MAX_FOOD
        self.max_food = config.SOLDIER_MAX_FOOD
        self.ammo = config.SOLDIER_MAX_AMMO
        self.max_ammo = config.SOLDIER_MAX_AMMO
        self.turns_without_food = 0
        self.wound_level = WOUND_NONE  # Уровень ранения
        self.wound_turns = 0           # Ходы с ранением (для выздоровления)
        self.is_medic = False           # Является ли санитаром

    @property
    def is_alive(self):
        return self._is_alive

    @is_alive.setter
    def is_alive(self, value):
        if getattr(self, '_is_alive', False) and not value:
            Soldier._global_dead_count += 1
        self._is_alive = value
    
    @property
    def full_name(self):
        return f"{self.surname} {self.name}"
    
    @property
    def short_name(self):
        return f"{self.surname} {self.name[0]}."
    
    @property
    def skills_str(self):
        return ", ".join(self.skills) if self.skills else "—"
    
    @property
    def effective_skill(self):
        base = len(self.skills) * 5 + self.experience
        morale_mod = self.morale / 100
        health_mod = self.health / 100
        wound_mod = 1.0 + WOUND_PENALTIES[self.wound_level]["attack"] / 100
        return int(base * morale_mod * health_mod * wound_mod)

    @property
    def weight(self):
        return config.SOLDIER_WEIGHT
    
    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        # Определяем уровень ранения по здоровью
        if self.health > 75:
            self.wound_level = WOUND_NONE
        elif self.health > 50:
            self.wound_level = WOUND_LIGHT
        elif self.health > 25:
            self.wound_level = WOUND_MEDIUM
        else:
            self.wound_level = WOUND_HEAVY
        if self.health <= 0:
            self.is_alive = False
            self.morale = 0
    
    def heal(self, amount):
        self.health = min(100, self.health + amount)
        # Обновляем уровень ранения
        if self.health > 75:
            self.wound_level = WOUND_NONE
        elif self.health > 50:
            self.wound_level = WOUND_LIGHT
        elif self.health > 25:
            self.wound_level = WOUND_MEDIUM
        else:
            self.wound_level = WOUND_HEAVY
    
    def treat_wound(self, medic_skill=0):
        """Лечение ранения санитаром. Возвращает True если лечение успешно"""
        if self.wound_level == WOUND_NONE:
            return False
        # Шанс лечения зависит от навыка санитара
        base_chance = 30 + medic_skill * 10
        if random.randint(1, 100) <= base_chance:
            # Улучшаем ранение на 1 уровень
            if self.wound_level > WOUND_NONE:
                self.wound_level -= 1
                # Восстанавливаем здоровье в зависимости от нового уровня
                if self.wound_level == WOUND_NONE:
                    self.health = max(self.health, 80)
                elif self.wound_level == WOUND_LIGHT:
                    self.health = max(self.health, 55)
                elif self.wound_level == WOUND_MEDIUM:
                    self.health = max(self.health, 30)
                return True
        return False
    
    def gain_experience(self, amount):
        self.experience = min(100, self.experience + amount)
    
    def change_morale(self, amount):
        self.morale = max(0, min(100, self.morale + amount))
    
    def to_dict(self):
        return {
            "name": self.name,
            "surname": self.surname,
            "gender": self.gender,
            "skills": self.skills,
            "experience": self.experience,
            "morale": self.morale,
            "health": self.health,
            "is_alive": self.is_alive,
            "role": self.role,
            "food": self.food,
            "max_food": self.max_food,
            "ammo": self.ammo,
            "max_ammo": self.max_ammo,
            "turns_without_food": self.turns_without_food,
            "wound_level": self.wound_level,
            "wound_turns": self.wound_turns,
            "is_medic": self.is_medic,
        }
    
    @classmethod
    def from_dict(cls, data):
        soldier = cls(
            name=data.get("name"),
            surname=data.get("surname"),
            gender=data.get("gender"),
            skills=data.get("skills"),
            role=data.get("role", "Солдат"),
        )
        soldier.experience = data.get("experience", 0)
        soldier.morale = data.get("morale", 100)
        soldier.health = data.get("health", 100)
        soldier.is_alive = data.get("is_alive", True)
        soldier.food = data.get("food", config.SOLDIER_MAX_FOOD)
        soldier.max_food = data.get("max_food", config.SOLDIER_MAX_FOOD)
        soldier.ammo = data.get("ammo", config.SOLDIER_MAX_AMMO)
        soldier.max_ammo = data.get("max_ammo", config.SOLDIER_MAX_AMMO)
        soldier.turns_without_food = data.get("turns_without_food", 0)
        soldier.wound_level = data.get("wound_level", WOUND_NONE)
        soldier.wound_turns = data.get("wound_turns", 0)
        soldier.is_medic = data.get("is_medic", False)
        return soldier
    
    def consume_food(self):
        """Consume food every FOOD_CONSUMPTION_INTERVAL turns"""
        self.food -= config.SOLDIER_FOOD_PER_TURN
        if self.food <= 0:
            self.turns_without_food += 1
            if self.turns_without_food >= config.SOLDIER_TURNS_WITHOUT_FOOD_DEATH:
                self.is_alive = False
                self.morale = 0
        else:
            self.turns_without_food = 0

    def __repr__(self):
        wound_str = f", {WOUND_NAMES[self.wound_level]}" if self.wound_level > WOUND_NONE else ""
        return f"Soldier({self.full_name}, {self.role}, skills: {self.skills_str}, exp: {self.experience}, morale: {self.morale}, hp: {self.health}{wound_str}, food: {self.food}/{self.max_food}, ammo: {self.ammo}/{self.max_ammo})"


class Unit:
    TRAIL_LENGTH = 20

    def __init__(self, x, y, unit_type, faction, name, game_map=None):
        self.x = x
        self.y = y
        self.type = unit_type
        self.faction = faction
        self.name = name
        self.alive = True
        self.moved = False
        self.attacked = False
        self.entrenching = False
        self.stationary_turns = 0
        self.trail = [(x, y)]
        self.game_map = game_map

    @property
    def is_jammer(self):
        return False

    @property
    def is_alive(self):
        return self.alive

    @property
    def vision_range(self):
        return config.VISION_RANGE.get(self.type, 2)

    def get_movement_cost(self, terrain):
        return config.TERRAIN_MOVEMENT_COST.get(terrain, 1)

    def die(self):
        self.alive = False

    def reset_turn(self):
        self.moved = False
        self.attacked = False

    def status_lines(self):
        return []

    @property
    def is_radar_source(self):
        return False

    def _generate_crew(self, count):
        roles = ["Командир", "Стрелок", "Сапёр", "Санитар"]
        soldiers = []
        for i in range(count):
            s = Soldier()
            if i < len(roles):
                s.role = roles[i]
            else:
                s.role = "Член экипажа"
            soldiers.append(s)
        return soldiers


class Infantry(Unit):
    NORMAL_SQUAD_SIZE = 8

    def __init__(self, x, y, faction, name="Пехота", soldiers=None):
        super().__init__(x, y, config.INFANTRY, faction, name)
        self.max_soldiers = config.INFANTRY_MAX_SOLDIERS
        self.ammo = config.INFANTRY_MAX_AMMO
        self.max_ammo = config.INFANTRY_MAX_AMMO
        self.food = 0
        self.max_food = 0
        self.max_entrenchment = config.INFANTRY_MAX_ENTRENCH
        self.morale = config.INFANTRY_MORALE_MAX
        self.turns_without_food = 0
        self.color = (50, 50, 220) if faction == config.PLAYER else (180, 50, 50)
        self.building_cache = None
        self.loaded_in_truck = False
        self.transport_vehicle = None

        if soldiers is not None:
            if isinstance(soldiers, int):
                self.soldiers_list = self._generate_soldiers(soldiers)
            else:
                self.soldiers_list = soldiers
        else:
            self.soldiers_list = self._generate_soldiers(config.INFANTRY_INIT_SOLDIERS)
    
    @property
    def carry_capacity(self):
        return self.soldiers * config.SOLDIER_CARRY_CAPACITY

    @property
    def total_food_carried(self):
        return sum(s.food for s in self.alive_soldiers)

    @property
    def is_overloaded(self):
        return self.total_food_carried > self.carry_capacity

    @property
    def overload_ratio(self):
        if self.carry_capacity == 0:
            return 0
        return max(0, (self.total_food_carried - self.carry_capacity) / self.carry_capacity)
    
    def _generate_soldiers(self, count):
        soldiers = []
        for _ in range(count):
            soldiers.append(Soldier())
        return soldiers
    
    @property
    def soldiers(self):
        return len([s for s in self.soldiers_list if s.is_alive])
    
    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]
    
    @property
    def dead_soldiers(self):
        return [s for s in self.soldiers_list if not s.is_alive]
    
    def add_soldier(self, soldier):
        if len(self.soldiers_list) < self.max_soldiers:
            self.soldiers_list.append(soldier)
            return True
        return False
    
    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False
    
    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False
    
    def load_into_truck(self, truck):
        """Load this infantry unit into a supply truck"""
        from . import config
        if not isinstance(truck, SupplyTruck) or not truck.is_alive:
            return False
        if self.loaded_in_truck:
            return False
        if len(truck.alive_soldiers) + self.soldiers > truck.max_soldiers:
            return False
        # Transfer all soldiers to truck
        for soldier in self.alive_soldiers:
            self.remove_soldier(soldier)
            truck.add_soldier(soldier)
        self.loaded_in_truck = True
        self.transport_vehicle = truck
        self.x, self.y = truck.x, truck.y
        return True
    
    def unload_from_truck(self, x, y):
        """Unload this infantry unit from truck at position x, y"""
        if not self.loaded_in_truck or not self.transport_vehicle:
            return False
        truck = self.transport_vehicle
        # Transfer soldiers back
        soldiers_to_transfer = truck.alive_soldiers[:self.max_soldiers]
        for soldier in soldiers_to_transfer:
            truck.remove_soldier(soldier)
            self.add_soldier(soldier)
        self.loaded_in_truck = False
        self.transport_vehicle = None
        self.x, self.y = x, y
        return True
    
    def get_average_morale(self):
        alive = self.alive_soldiers
        if not alive:
            return 0
        return sum(s.morale for s in alive) // len(alive)
    
    def get_average_experience(self):
        alive = self.alive_soldiers
        if not alive:
            return 0
        return sum(s.experience for s in alive) // len(alive)
    
    def get_average_health(self):
        alive = self.alive_soldiers
        if not alive:
            return 0
        return sum(s.health for s in alive) // len(alive)

    def die(self):
        self.building_cache = None
        super().die()

    @property
    def vision_range(self):
        return config.VISION_RANGE["infantry"]

    @property
    def attack_power(self):
        base = max(1, self.soldiers // 2)
        if self.is_overloaded:
            base = max(1, int(base * (1 - self.overload_ratio * 0.5)))
        # Штраф за раненых бойцов
        wounded_penalty = self._get_wound_penalty()
        base = max(1, int(base * (1 - wounded_penalty)))
        return base

    def _get_wound_penalty(self):
        """Получить общий штраф за ранения в отряде"""
        alive = self.alive_soldiers
        if not alive:
            return 0
        total_penalty = sum(WOUND_PENALTIES[s.wound_level]["attack"] for s in alive)
        return abs(total_penalty) / (len(alive) * 100)

    @property
    def hit_chance(self):
        base = config.INFANTRY_BASE_HIT_CHANCE
        if self.morale < 30:
            base -= 20
        n = self.soldiers
        if n > self.NORMAL_SQUAD_SIZE:
            base -= (n - self.NORMAL_SQUAD_SIZE) * 2
        if self.is_overloaded:
            base -= int(self.overload_ratio * 30)
        any_hungry = any(s.food <= 0 for s in self.alive_soldiers)
        if any_hungry:
            base -= 15
        # Штраф за раненых
        wound_penalty = self._get_wound_penalty()
        base -= int(wound_penalty * 30)
        return max(10, base)

    @property
    def effective_move_speed(self):
        speed = 1
        if self.is_overloaded:
            speed = max(1, 1 - int(self.overload_ratio * 1))
        return speed

    @property
    def camouflage(self):
        base = 40
        n = self.soldiers
        if n > self.NORMAL_SQUAD_SIZE:
            base -= (n - self.NORMAL_SQUAD_SIZE) * 5
        if self.game_map:
            cell = self.game_map.get_cell(self.x, self.y)
            if cell.entrenchment > 50:
                base += 10
        if self.is_overloaded:
            base -= int(self.overload_ratio * 20)
        return max(0, min(100, base))

    def get_movement_cost(self, terrain):
        return config.TERRAIN_MOVEMENT_COST.get(terrain, 1)

    def entrench_step(self, game_map):
        cell = game_map.get_cell(self.x, self.y)
        if cell and cell.entrenchment < self.max_entrenchment:
            cell.entrenchment = min(self.max_entrenchment, cell.entrenchment + 20)

    def consume_food(self, current_turn):
        for s in self.alive_soldiers:
            s.consume_food()
        self.share_resources()
        if not any(s.is_alive for s in self.alive_soldiers):
            self.die()
        self._apply_overcrowd_penalties()

    def share_resources(self):
        alive = self.alive_soldiers
        if len(alive) <= 1:
            return
        total_food = sum(s.food for s in alive)
        total_ammo = sum(s.ammo for s in alive)
        n = len(alive)
        avg_food = total_food // n
        avg_ammo = total_ammo // n
        for s in alive:
            if s.food < avg_food and total_food > 0:
                deficit = avg_food - s.food
                available = min(deficit, total_food)
                s.food += available
                total_food -= available
            if s.ammo < avg_ammo and total_ammo > 0:
                deficit = avg_ammo - s.ammo
                available = min(deficit, total_ammo)
                s.ammo += available
                total_ammo -= available

    def treat_wounded(self):
        """Лечение раненых санитарами отряда. Возвращает количество вылеченных"""
        alive = self.alive_soldiers
        medics = [s for s in alive if s.is_medic or "Медицина" in s.skills]
        wounded = [s for s in alive if s.wound_level > WOUND_NONE]
        
        if not medics or not wounded:
            return 0
        
        treated = 0
        for medic in medics:
            medic_skill = len(medic.skills) + (1 if "Медицина" in medic.skills else 0)
            for patient in wounded:
                if patient.treat_wound(medic_skill):
                    treated += 1
                    if patient not in alive:
                        break
        
        return treated

    def _apply_overcrowd_penalties(self):
        n = self.soldiers
        if n > self.NORMAL_SQUAD_SIZE:
            overcrowd = n - self.NORMAL_SQUAD_SIZE
            self.morale = max(0, self.morale - overcrowd)

    def take_damage(self, amount, game_map=None):
        entrench = 0
        gm = game_map or self.game_map
        if gm:
            cell = gm.get_cell(self.x, self.y)
            entrench = cell.entrenchment
        absorbed = int(amount * entrench / 200)
        absorbed += int(amount * config.TERRAIN_DEFENSE_BONUS.get(0, 0) / 200)
        actual = max(1, amount - absorbed)
        alive = self.alive_soldiers
        to_kill = min(len(alive), actual)
        for s in random.sample(alive, to_kill):
            s.is_alive = False
        if self.soldiers <= 0:
            self.die()

    def take_fpv_damage(self, game_map=None):
        dmg = config.FPV_DAMAGE_INFANTRY
        entrench = 0
        gm = game_map or self.game_map
        if gm:
            cell = gm.get_cell(self.x, self.y)
            entrench = cell.entrenchment
        absorbed = int(dmg * entrench / 200)
        actual = max(1, dmg - absorbed)
        alive = self.alive_soldiers
        to_kill = min(len(alive), actual)
        for s in random.sample(alive, to_kill):
            s.is_alive = False
        if self.soldiers <= 0:
            self.die()
        return actual

    def attack_infantry(self, target, game_map=None):
        total_ammo = sum(s.ammo for s in self.alive_soldiers)
        if total_ammo <= 0:
            return 0, "Нет боезапаса"
        for s in self.alive_soldiers:
            if s.ammo > 0:
                s.ammo -= 1
                break
        hit = random.randint(1, 100) <= self.hit_chance
        if not hit:
            return 0, "Промах"
        entrench = 0
        gm = game_map or self.game_map
        if gm:
            cell = gm.get_cell(target.x, target.y)
            entrench = cell.entrenchment
        dmg = max(1, self.attack_power - entrench // 20)
        target.take_damage(dmg, gm)
        return dmg, "Попадание"

    def status_lines(self):
        n = self.soldiers
        total_food = self.total_food_carried
        total_ammo = sum(s.ammo for s in self.alive_soldiers)
        entrench = 0
        if self.game_map:
            cell = self.game_map.get_cell(self.x, self.y)
            entrench = cell.entrenchment
        lines = [
            f"Люди: {n}/{self.max_soldiers}",
            f"Боезапас: {total_ammo}",
            f"Еда: {total_food}",
            f"Укрепление: {entrench}%",
            f"Мораль: {self.morale}",
        ]
        # Информация о раненых
        wounded_count = len([s for s in self.alive_soldiers if s.wound_level > WOUND_NONE])
        if wounded_count > 0:
            lines.append(f"Раненые: {wounded_count}")
        if self.is_overloaded:
            lines.append(f"Перегруз: {int(self.overload_ratio * 100)}%")
        if self.building_cache:
            lines.append(f"Строит погреб: {self.building_cache.build_turns}/{self.building_cache.build_required}")
        return lines


class SoldierUnit(Unit):
    def __init__(self, x, y, faction, soldier, name=None):
        super().__init__(x, y, "soldier_unit", faction, name or soldier.full_name)
        self.soldier = soldier
        self.color = (80, 180, 80) if faction == config.PLAYER else (200, 100, 80)
        self.target_x = None
        self.target_y = None
        # Personal reserves from the soldier
        self.food = soldier.food
        self.max_food = soldier.max_food
        self.ammo = soldier.ammo
        self.max_ammo = soldier.max_ammo
        self.turns_without_food = 0

    @property
    def is_alive(self):
        return self.alive and self.soldier.is_alive

    @property
    def vision_range(self):
        return 2

    def set_destination(self, tx, ty):
        self.target_x = tx
        self.target_y = ty

    def move_step(self, game_map):
        if self.target_x is None or self.target_y is None:
            return False
        if self.x == self.target_x and self.y == self.target_y:
            return False
        dx = 1 if self.target_x > self.x else (-1 if self.target_x < self.x else 0)
        dy = 1 if self.target_y > self.y else (-1 if self.target_y < self.y else 0)
        candidates = []
        if dx != 0 and dy != 0:
            candidates = [(dx, dy), (dx, 0), (0, dy), (-dx, dy), (dx, -dy)]
        elif dx != 0:
            candidates = [(dx, 0), (dx, 1), (dx, -1), (0, 1), (0, -1)]
        elif dy != 0:
            candidates = [(0, dy), (1, dy), (-1, dy), (1, 0), (-1, 0)]
        else:
            return False
        for cdx, cdy in candidates:
            nx, ny = self.x + cdx, self.y + cdy
            if not (0 <= nx < game_map.width and 0 <= ny < game_map.height):
                continue
            cell = game_map.get_cell(nx, ny)
            if not cell:
                continue
            blocked = False
            for u in cell.units:
                if u is not self and u.is_alive:
                    if nx == self.target_x and ny == self.target_y:
                        game_map.remove_unit(self)
                        self.x, self.y = nx, ny
                        game_map.add_unit(self, nx, ny)
                        self.trail.append((nx, ny))
                        return True
                    blocked = True
                    break
            if not blocked:
                game_map.remove_unit(self)
                self.x, self.y = nx, ny
                game_map.add_unit(self, nx, ny)
                self.trail.append((nx, ny))
                return True
        return False

    @property
    def direction_angle(self):
        if self.target_x is None or self.target_y is None:
            return None
        import math
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if dx == 0 and dy == 0:
            return None
        return math.atan2(dy, dx)

    def try_join_unit(self, target_unit):
        if not target_unit or not target_unit.is_alive:
            return False
        if not hasattr(target_unit, 'add_soldier'):
            return False
        dist = abs(self.x - target_unit.x) + abs(self.y - target_unit.y)
        if dist > 1:
            return False
        if target_unit.add_soldier(self.soldier):
            self.die()
            return True
        return False

    def take_damage(self, amount):
        self.soldier.health = max(0, self.soldier.health - amount)
        if self.soldier.health <= 0:
            self.soldier.is_alive = False
            self.die()

    def die(self):
        self.alive = False

    def consume_food(self):
        """Consume food every FOOD_CONSUMPTION_INTERVAL turns"""
        self.soldier.consume_food()
        self.food = self.soldier.food
        self.turns_without_food = self.soldier.turns_without_food
        if not self.soldier.is_alive:
            self.die()

    def status_lines(self):
        s = self.soldier
        lines = [
            f"{s.full_name}",
            f"Здоровье: {s.health}%",
            f"Мораль: {s.morale}%",
            f"Навыки: {s.skills_str}",
            f"Еда: {self.food}/{self.max_food}",
            f"Боезапас: {self.ammo}/{self.max_ammo}",
        ]
        # Информация о ранении
        if s.wound_level > WOUND_NONE:
            lines.append(f"Состояние: {WOUND_NAMES[s.wound_level]}")
        if self.target_x is not None:
            lines.append(f"Цель: ({self.target_x},{self.target_y})")
        return lines


class Tank(Unit):
    def __init__(self, x, y, faction, name="Танк"):
        super().__init__(x, y, config.TANK, faction, name)
        self.max_crew = config.TANK_MAX_CREW
        self.armor = config.TANK_MAX_ARMOR
        self.max_armor = config.TANK_MAX_ARMOR
        self.ammo = config.TANK_MAX_AMMO
        self.max_ammo = config.TANK_MAX_AMMO
        self.fuel = config.TANK_MAX_FUEL
        self.max_fuel = config.TANK_MAX_FUEL
        self.carry_food = 100
        self.max_carry_food = 200
        self.carry_ammo = 0
        self.max_carry_ammo = config.TANK_CARRY_CAPACITY
        self.color = (50, 50, 220) if faction == config.PLAYER else (180, 50, 50)
        self.soldiers_list = self._generate_crew(config.TANK_INIT_CREW)
        self.min_crew = config.TANK_MIN_CREW

    @property
    def is_jammer(self):
        return True

    def _generate_crew(self, count):
        roles = ["Механик-водитель", "Командир", "Наводчик", "Заряжающий"]
        soldiers = []
        for i in range(count):
            s = Soldier()
            if i < len(roles):
                s.role = roles[i]
            else:
                s.role = "Член экипажа"
            s.food = 100
            s.max_food = 200
            soldiers.append(s)
        return soldiers

    @property
    def crew(self):
        return len([s for s in self.soldiers_list if s.is_alive])

    @crew.setter
    def crew(self, value):
        alive = [s for s in self.soldiers_list if s.is_alive]
        dead = [s for s in self.soldiers_list if not s.is_alive]
        while len(alive) > value and alive:
            alive[-1].is_alive = False
            alive.pop()
        while len(alive) < value and len(alive) < self.max_crew:
            s = Soldier()
            s.food = 100
            s.max_food = 200
            alive.append(s)
        self.soldiers_list = alive + dead

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]

    @property
    def dead_soldiers(self):
        return [s for s in self.soldiers_list if not s.is_alive]

    @property
    def max_soldiers(self):
        return self.max_crew

    @property
    def is_understaffed(self):
        return len(self.alive_soldiers) < self.min_crew

    def add_soldier(self, soldier):
        if len(self.alive_soldiers) < self.max_crew:
            soldier.food = max(soldier.food, 100)
            soldier.max_food = max(soldier.max_food, 200)
            self.soldiers_list.append(soldier)
            return True
        return False

    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False

    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False

    @property
    def vision_range(self):
        return config.VISION_RANGE["tank"]

    @property
    def attack_power(self):
        return 3

    @property
    def hit_chance(self):
        return config.TANK_BASE_HIT_CHANCE

    def get_movement_cost(self, terrain):
        cost = config.TERRAIN_MOVEMENT_COST.get(terrain, 1)
        if terrain == config.ROAD:
            cost *= 0.5  # Бонус 50% для техники на дороге
        return cost

    def attack(self, target):
        if self.ammo <= 0:
            return 0, "Нет снарядов"
        self.ammo -= 1
        if random.randint(1, 100) <= self.hit_chance:
            if isinstance(target, Tank) and random.randint(1, 100) <= 30:
                return 0, "Рикошет"
            dmg = self.attack_power
            if isinstance(target, Infantry):
                dmg = min(target.soldiers, dmg + 2)
            target.take_damage(dmg)
            return dmg, "Попадание"
        return 0, "Промах"

    def take_damage(self, amount):
        absorbed = min(amount, self.armor // 10)
        actual = max(1, amount - absorbed)
        alive = self.alive_soldiers
        to_kill = min(len(alive), actual)
        for s in random.sample(alive, to_kill):
            s.is_alive = False
        self.armor = max(0, self.armor - amount)
        if self.crew <= 0:
            self.die()

    def consume_food(self):
        for s in self.alive_soldiers:
            s.consume_food()

    def status_lines(self):
        total_carry = self.carry_food + self.carry_ammo
        lines = [
            f"Экипаж: {self.crew}/{self.max_crew}",
            f"Броня: {self.armor}/{self.max_armor}",
            f"Снаряды: {self.ammo}/{self.max_ammo}",
            f"Топливо: {self.fuel}/{self.max_fuel}",
        ]
        if self.carry_food > 0 or self.carry_ammo > 0:
            lines.append(f"Груз: еда {self.carry_food}, б/з {self.carry_ammo}")
        return lines


class Artillery(Unit):
    def __init__(self, x, y, faction, name="Артиллерия"):
        super().__init__(x, y, config.ARTILLERY, faction, name)
        self.ammo = config.ARTILLERY_MAX_AMMO
        self.max_ammo = config.ARTILLERY_MAX_AMMO
        self.max_crew = config.ARTILLERY_MAX_CREW
        self.max_entrenchment = config.ARTILLERY_MAX_ENTRENCH
        self.pending_target = None
        self.color = (100, 50, 150) if faction == config.PLAYER else (150, 50, 100)
        self.soldiers_list = self._generate_crew(config.ARTILLERY_INIT_CREW)

    def _generate_crew(self, count):
        roles = ["Командир орудия", "Наводчик", "Заряжающий", "Подносчик", "Радист", "Наблюдатель"]
        soldiers = []
        for i in range(count):
            s = Soldier()
            if i < len(roles):
                s.role = roles[i]
            else:
                s.role = "Член расчёта"
            s.food = 100
            s.max_food = 200
            soldiers.append(s)
        return soldiers

    @property
    def crew(self):
        return len([s for s in self.soldiers_list if s.is_alive])

    @crew.setter
    def crew(self, value):
        alive = [s for s in self.soldiers_list if s.is_alive]
        dead = [s for s in self.soldiers_list if not s.is_alive]
        while len(alive) > value and alive:
            alive[-1].is_alive = False
            alive.pop()
        while len(alive) < value and len(alive) < self.max_crew:
            s = Soldier()
            s.food = 100
            s.max_food = 200
            alive.append(s)
        self.soldiers_list = alive + dead

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]

    @property
    def dead_soldiers(self):
        return [s for s in self.soldiers_list if not s.is_alive]

    @property
    def max_soldiers(self):
        return self.max_crew

    def add_soldier(self, soldier):
        if len(self.alive_soldiers) < self.max_crew:
            soldier.food = max(soldier.food, 100)
            soldier.max_food = max(soldier.max_food, 200)
            self.soldiers_list.append(soldier)
            return True
        return False

    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False

    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False

    @property
    def vision_range(self):
        return config.VISION_RANGE["artillery"]

    @property
    def attack_range(self):
        return config.ARTILLERY_ATTACK_RANGE

    @property
    def attack_power(self):
        return config.ARTILLERY_DAMAGE

    def get_movement_cost(self, terrain):
        cost = config.TERRAIN_MOVEMENT_COST.get(terrain, 1)
        if terrain == config.ROAD:
            cost *= 0.5  # Бонус 50% для техники на дороге
        return cost

    def attack_cell(self, game_map, all_units, target_x, target_y, max_range=None):
        """Атака выбранной клетки"""
        if self.ammo <= 0:
            return 0, "Нет снарядов", []
        
        self.ammo -= 1
        self.attacked = True
        
        # Проверяем дистанцию
        effective_range = max_range if max_range is not None else self.attack_range
        dist = abs(self.x - target_x) + abs(self.y - target_y)
        if dist > effective_range:
            self.ammo += 1
            self.attacked = False
            return 0, "Цель вне досягаемости", []
        
        # Определяем шанс попадания по типу местности
        cell = game_map.get_cell(target_x, target_y)
        if not cell:
            self.ammo += 1
            self.attacked = False
            return 0, "Нет клетки", []
        
        base_hit_chance = 80  # Поле / дорога
        if cell.terrain == config.FOREST:
            base_hit_chance = 60
        elif cell.terrain == config.CITY:
            base_hit_chance = 40
        
        # Учитываем укрепления цели (только для пехоты с entrenchment)
        entrench_penalty = 0
        cell = game_map.get_cell(target_x, target_y)
        if cell:
            entrench_penalty = cell.entrenchment // 2
        
        hit_chance = max(10, base_hit_chance - entrench_penalty)
        
        # Проверяем попадание
        roll = random.randint(1, 100)
        if roll > hit_chance:
            return 0, f"Промах ({hit_chance}% шанс)", []
        
        # Урон только по целевой клетке
        damaged_units = []
        total_damage = 0
        
        for unit in all_units:
            if unit.x == target_x and unit.y == target_y and unit.is_alive:
                if hasattr(unit, 'is_flying') and unit.is_flying:
                    continue
                
                damage = self.attack_power
                
                # Модификаторы местности (урон)
                if cell.terrain == config.FOREST:
                    damage = int(damage * 0.7)
                elif cell.terrain == config.CITY:
                    damage = int(damage * 0.8)
                
                # Модификатор укрепления (урон)
                if game_map:
                    cell = game_map.get_cell(target_x, target_y)
                    damage = int(damage * (1 - cell.entrenchment / 200))
                
                damage = max(1, damage)
                
                if isinstance(unit, Infantry):
                    unit.take_damage(damage, game_map)
                elif isinstance(unit, Tank):
                    unit.take_damage(damage)
                elif isinstance(unit, Artillery):
                    unit.take_damage(damage)
                elif isinstance(unit, SupplyTruck):
                    unit.take_damage(damage)
                
                damaged_units.append((unit, damage))
                total_damage += damage
        
        return total_damage, "Попадание", damaged_units

    def take_damage(self, amount, game_map=None):
        entrench = 0
        gm = game_map or self.game_map
        if gm:
            cell = gm.get_cell(self.x, self.y)
            entrench = cell.entrenchment
        absorbed = int(amount * entrench / 200)
        actual = max(1, amount - absorbed)
        alive = self.alive_soldiers
        to_kill = min(len(alive), actual)
        for s in random.sample(alive, to_kill):
            s.is_alive = False
        if self.crew <= 0:
            self.die()

    def status_lines(self):
        entrench = 0
        if self.game_map:
            cell = self.game_map.get_cell(self.x, self.y)
            entrench = cell.entrenchment
        lines = [
            f"Экипаж: {self.crew}/{self.max_crew}",
            f"Снаряды: {self.ammo}/{self.max_ammo}",
            f"Дальность: {self.attack_range} кл.",
            f"Укрепление: {entrench}%",
        ]
        if self.pending_target:
            tx, ty = self.pending_target
            lines.append(f"Обстрел: ({tx},{ty}) след. ход")
        return lines


class RadarEW(Unit):
    def __init__(self, x, y, faction, name="Радар РЭБ"):
        super().__init__(x, y, config.RADAR_EW, faction, name)
        self.max_crew = config.RADAR_EW_MAX_CREW
        self.food = config.RADAR_EW_MAX_FOOD
        self.max_food = config.RADAR_EW_MAX_FOOD
        self.ammo = config.RADAR_EW_MAX_AMMO
        self.max_ammo = config.RADAR_EW_MAX_AMMO
        self.fuel = config.RADAR_EW_MAX_FUEL
        self.max_fuel = config.RADAR_EW_MAX_FUEL
        self.morale = 100
        self.color = (200, 150, 50) if faction == config.PLAYER else (150, 50, 200)
        self.soldiers_list = self._generate_crew(config.RADAR_EW_INIT_CREW)
        self.min_crew = config.RADAR_EW_MIN_CREW
        self.turns_without_food = 0
        self.active = False
        self.jam_range = config.RADAR_EW_JAM_RANGE

    @property
    def is_jammer(self):
        return self.active and self.fuel > 0 and self.crew >= self.min_crew

    def _generate_crew(self, count):
        roles = ["Оператор РЭБ", "Радист", "Механик", "Наблюдатель"]
        soldiers = []
        for i in range(count):
            s = Soldier()
            if i < len(roles):
                s.role = roles[i]
            else:
                s.role = "Член расчёта"
            s.food = 100
            s.max_food = 200
            soldiers.append(s)
        return soldiers

    @property
    def crew(self):
        return len([s for s in self.soldiers_list if s.is_alive])

    @crew.setter
    def crew(self, value):
        alive = [s for s in self.soldiers_list if s.is_alive]
        dead = [s for s in self.soldiers_list if not s.is_alive]
        while len(alive) > value and alive:
            alive[-1].is_alive = False
            alive.pop()
        while len(alive) < value and len(alive) < self.max_crew:
            s = Soldier()
            s.food = 100
            s.max_food = 200
            alive.append(s)
        self.soldiers_list = alive + dead

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]

    @property
    def dead_soldiers(self):
        return [s for s in self.soldiers_list if not s.is_alive]

    @property
    def max_soldiers(self):
        return self.max_crew

    def add_soldier(self, soldier):
        if len(self.alive_soldiers) < self.max_crew:
            soldier.food = max(soldier.food, 100)
            soldier.max_food = max(soldier.max_food, 200)
            self.soldiers_list.append(soldier)
            return True
        return False

    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False

    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False

    @property
    def vision_range(self):
        return config.VISION_RANGE["radar_ew"]

    def take_damage(self, amount):
        alive = self.alive_soldiers
        to_kill = min(len(alive), amount)
        for s in random.sample(alive, to_kill):
            s.is_alive = False
        if self.crew <= 0:
            self.die()

    def consume_food(self):
        n = self.crew
        food_cost = max(1, n)
        self.food -= food_cost
        for s in self.alive_soldiers:
            s.consume_food()
        if self.food <= 0:
            self.turns_without_food += 1
            if self.turns_without_food >= 2:
                self.morale = max(0, self.morale - 10)
        else:
            self.turns_without_food = 0
        if self.active:
            self.fuel = max(0, self.fuel - config.RADAR_EW_FUEL_PER_TURN)
            if self.fuel <= 0:
                self.active = False

    def toggle(self):
        if not self.active and self.fuel <= 0:
            return False
        self.active = not self.active
        return self.active

    def get_movement_cost(self, terrain):
        cost = config.TERRAIN_MOVEMENT_COST.get(terrain, 1)
        if terrain == config.ROAD:
            cost *= 0.5  # Бонус 50% для техники на дороге
        return cost

    def status_lines(self):
        return [
            f"Экипаж: {self.crew}/{self.max_crew}",
            f"Дальность РЭБ: {self.jam_range} кл.",
            f"РЭБ: {'ВКЛ' if self.active else 'ВЫКЛ'}",
            f"Топливо: {self.fuel}/{self.max_fuel}",
            f"Еда: {self.food}/{self.max_food}",
            f"Мораль: {self.morale}%",
        ]


class ReconDrone(Unit):
    is_flying = True

    def __init__(self, x, y, faction, name="Дрон-разведчик"):
        super().__init__(x, y, config.RECON_DRONE, faction, name)
        self.battery = config.DRONE_MAX_BATTERY
        self.max_battery = config.DRONE_MAX_BATTERY
        self.color = (50, 150, 200) if faction == config.PLAYER else (200, 100, 50)
        self.can_fpv_strike = True
        self.operator = None
        self.jammed = False
        self.jam_turns = 0

    @property
    def vision_range(self):
        return config.DRONE_VISION_RANGE

    def get_movement_cost(self, terrain):
        return 1  # Дрон летает - стоимость всегда 1

    def consume_battery(self):
        self.battery -= 1
        if self.battery <= 0:
            self.can_fpv_strike = False

    def take_damage(self, amount):
        self.die()

    def status_lines(self):
        return [
            f"Батарея: {self.battery}/{self.max_battery}",
            f"Обзор: {self.vision_range} кл.",
        ]


class FPVDrone(Unit):
    def __init__(self, x, y, faction, target, name="FPV-дрон"):
        super().__init__(x, y, config.FPV_DRONE, faction, name)
        self.target = target
        self.speed = config.FPV_MOVE_SPEED
        self.color = (200, 50, 200)
        self.reached = False
        self.attacked = False
        self.shot_down = False
        self.hit_target = False
        self.moved = False

    @property
    def vision_range(self):
        return 2

    def get_movement_cost(self, terrain):
        return 1  # Дрон летает - стоимость всегда 1

    def get_movement_cost(self, terrain):
        return 1

    def _calc_ew_penalty(self, game_map, target):
        penalty = 0
        x1, y1 = self.x, self.y
        x2, y2 = target.x, target.y
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steps = max(dx, dy)
        if steps == 0:
            return 0
        
        for i in range(steps + 1):
            t = i / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            
            cell = game_map.get_cell(x, y)
            if cell:
                for unit in cell.units:
                    if unit.is_alive and unit.is_jammer:
                        if isinstance(unit, RadarEW):
                            penalty += 15
                        else:
                            penalty += 10
        return min(penalty, 50)

    def move_toward_target(self, game_map):
        if not self.target or not self.target.is_alive or self.reached:
            self.moved = True
            return
        
        # Проверяем видимость цели
        target_cell = game_map.get_cell(self.target.x, self.target.y)
        if target_cell and not target_cell.visible:
            self.reached = True
            self.moved = True
            return
        
        remaining = self.speed
        for _ in range(remaining):
            if self.reached:
                break
            dx = 1 if self.target.x > self.x else (-1 if self.target.x < self.x else 0)
            dy = 1 if self.target.y > self.y else (-1 if self.target.y < self.y else 0)
            if dx == 0 and dy == 0:
                self.reached = True
                break
            # Try primary direction first
            moved = False
            for ndx, ndy in [(dx, dy), (dy, dx), (-dy, -dx)]:
                nx, ny = self.x + (ndx if ndx != 0 else 0), self.y + (ndy if ndy != 0 else 0)
                # FPV ignores terrain - can fly anywhere
                if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                    game_map.remove_unit(self)
                    self.x, self.y = nx, ny
                    game_map.add_unit(self, nx, ny)
                    moved = True
                    break
            if not moved:
                self.reached = True
        self.moved = True
        dist = abs(self.x - self.target.x) + abs(self.y - self.target.y)
        if dist <= 1:
            self.reached = True

    def try_attack(self, game_map, combat_log, message_cb, recon_drones=None):
        if self.attacked or self.shot_down or not self.target or not self.target.is_alive:
            return
        self.attacked = True
        target = self.target

        # Проверяем видимость цели
        target_cell = game_map.get_cell(target.x, target.y)
        if target_cell and not target_cell.visible:
            msg = f"FPV потерял цель {target.name}! Цель не видна"
            combat_log.append({"message": msg})
            message_cb(msg)
            self.hit_target = False
            self.die()
            return

        # Infantry shootdown check
        shootdown_chance = 0
        if isinstance(target, Infantry) and target.soldiers > 0:
            shootdown_chance = config.FPV_INFANTRY_SHOOTDOWN_CHANCE
            cell = game_map.get_cell(target.x, target.y)
            if cell:
                for u in cell.units:
                    if isinstance(u, Infantry) and u.faction == target.faction and u.is_alive:
                        shootdown_chance += config.FPV_INFANTRY_SHOOTDOWN_CHANCE * 0.5

        if random.random() < shootdown_chance:
            self.shot_down = True
            self.die()
            msg = f"FPV сбит пехотой {target.name}!"
            combat_log.append({"message": msg})
            message_cb(msg)
            return

        # Calculate hit chance
        hit_chance = config.FPV_HIT_CHANCE_BASE
        if isinstance(target, Tank):
            hit_chance -= config.FPV_HIT_EW_PENALTY  # tanks have EW
        # No recon LOS penalty
        if recon_drones:
            has_los = False
            for rd in recon_drones:
                if game_map._has_los(rd.x, rd.y, target.x, target.y):
                    has_los = True
                    break
            if not has_los:
                hit_chance -= config.FPV_NO_LOS_PENALTY
        cell = game_map.get_cell(target.x, target.y)
        if cell:
            if cell.terrain == config.FOREST:
                hit_chance -= config.FPV_HIT_FOREST_PENALTY
            elif cell.terrain == config.CITY:
                hit_chance -= config.FPV_HIT_CITY_PENALTY

        # Штраф от РЭБ на пути следования дрона
        ew_penalty = self._calc_ew_penalty(game_map, target)
        hit_chance -= ew_penalty

        if random.random() > hit_chance:
            msg = f"FPV промахнулся по {target.name}!"
            combat_log.append({"message": msg})
            message_cb(msg)
            self.hit_target = False
            self.die()
            return

        # Hit!
        self.hit_target = True
        if isinstance(target, Infantry):
            dmg = target.take_fpv_damage(game_map)
        elif isinstance(target, Tank):
            dmg = config.FPV_DAMAGE_ARMOR
            target.take_damage(dmg)
        else:
            target.die()
            dmg = 99

        msg = f"FPV поразил {target.name}! Урон: {dmg}"
        combat_log.append({"message": msg, "damage": dmg})
        message_cb(msg)
        self.die()


class FPVOperator(Unit):
    def __init__(self, x, y, faction, name="FPV-расчёт"):
        super().__init__(x, y, config.FPV_OPERATOR, faction, name)
        self.max_crew = 999
        self.fpv_stock = config.FPV_OPERATOR_MAX_STOCK
        self.max_stock = config.FPV_OPERATOR_MAX_STOCK
        self.food = config.FPV_OPERATOR_MAX_FOOD
        self.max_food = config.FPV_OPERATOR_MAX_FOOD
        self.ammo = config.FPV_OPERATOR_MAX_AMMO
        self.max_ammo = config.FPV_OPERATOR_MAX_AMMO
        self.morale = 100
        self.auto_mode = True
        self.color = (180, 50, 180) if faction == config.PLAYER else (180, 50, 180)
        self.min_crew = config.FPV_OPERATOR_MIN_CREW
        self.soldiers_list = self._generate_crew(config.FPV_OPERATOR_INIT_CREW)
        self.turns_without_food = 0

    def _generate_crew(self, count):
        roles = ["Оператор FPV", "Заряжающий", "Наводчик"]
        soldiers = []
        for i in range(count):
            s = Soldier()
            if i < len(roles):
                s.role = roles[i]
            else:
                s.role = "Член расчёта"
            soldiers.append(s)
        return soldiers

    @property
    def crew(self):
        return len([s for s in self.soldiers_list if s.is_alive])

    @crew.setter
    def crew(self, value):
        alive = [s for s in self.soldiers_list if s.is_alive]
        dead = [s for s in self.soldiers_list if not s.is_alive]
        while len(alive) > value and alive:
            alive[-1].is_alive = False
            alive.pop()
        while len(alive) < value and len(alive) < self.max_crew:
            alive.append(Soldier())
        self.soldiers_list = alive + dead

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]

    @property
    def dead_soldiers(self):
        return [s for s in self.soldiers_list if not s.is_alive]

    @property
    def max_soldiers(self):
        return self.max_crew

    @property
    def is_understaffed(self):
        return len(self.alive_soldiers) < self.min_crew

    def add_soldier(self, soldier):
        if len(self.alive_soldiers) < self.max_crew:
            self.soldiers_list.append(soldier)
            return True
        return False

    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False

    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False

    @property
    def vision_range(self):
        return 2

    def take_damage(self, amount):
        self.die()

    def reload(self):
        if self.fpv_stock < self.max_stock:
            self.fpv_stock = min(self.max_stock, self.fpv_stock + 1)
        # Restore ammo when on warehouse
        if self.ammo < self.max_ammo:
            self.ammo = min(self.max_ammo, self.ammo + 5)

    def launch_fpv(self):
        if self.fpv_stock > 0:
            self.fpv_stock -= 1
            return True
        return False

    def consume_food(self):
        """Consume food every FOOD_CONSUMPTION_INTERVAL turns"""
        n = self.crew
        food_cost = max(1, n)
        self.food -= food_cost
        # Also consume each soldier's personal food
        for s in self.alive_soldiers:
            s.consume_food()
        if self.food <= 0:
            self.turns_without_food += 1
            if self.turns_without_food >= 2:
                self.morale = max(0, self.morale - 10)
        else:
            self.turns_without_food = 0

    def status_lines(self):
        return [
            f"FPV-дроны: {self.fpv_stock}/{self.max_stock}",
            f"Режим: {'Авто' if self.auto_mode else 'Ручной'}",
            f"Еда: {self.food}/{self.max_food}",
            f"Боезапас: {self.ammo}/{self.max_ammo}",
            f"Мораль: {self.morale}%",
        ]


class SupplyTruck(Unit):
    CARGO_CYCLE = [config.CARGO_SUPPLIES, config.CARGO_AMMO, config.CARGO_FUEL, config.CARGO_BATTERIES, config.CARGO_FPV_DRONE, config.CARGO_RECON_DRONE]

    def __init__(self, x, y, faction, name="Грузовик"):
        super().__init__(x, y, config.SUPPLY_TRUCK, faction, name)
        self.cargo = {t: 0 for t in self.CARGO_CYCLE}
        self.max_weight = config.TRUCK_MAX_WEIGHT
        self.fuel = config.TRUCK_MAX_FUEL
        self.max_fuel = config.TRUCK_MAX_FUEL
        self.load_choice = 0
        self.auto_mix = True
        self.supply_route = None
        self._route_origin = None
        self._route_dest = None
        self.color = (200, 180, 50) if faction == config.PLAYER else (180, 100, 50)
        self.max_soldiers = config.TRUCK_MAX_CREW
        self.min_crew = config.TRUCK_MIN_CREW
        self.soldiers_list = self._generate_crew(config.TRUCK_INIT_CREW)

    def _generate_crew(self, count):
        roles = ["Водитель", "Грузчик"]
        soldiers = []
        for i in range(count):
            s = Soldier()
            if i < len(roles):
                s.role = roles[i]
            else:
                s.role = "Член экипажа"
            s.food = 100
            s.max_food = 100
            soldiers.append(s)
        return soldiers

    @property
    def crew(self):
        return len([s for s in self.soldiers_list if s.is_alive])

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]

    @property
    def is_understaffed(self):
        return len(self.alive_soldiers) < self.min_crew

    def add_soldier(self, soldier):
        if len(self.alive_soldiers) < self.max_soldiers:
            soldier.food = max(soldier.food, 100)
            soldier.max_food = max(soldier.max_food, 100)
            self.soldiers_list.append(soldier)
            return True
        return False

    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False

    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False

    @property
    def current_load_type(self):
        return self.CARGO_CYCLE[self.load_choice]

    def cycle_load_type(self):
        self.load_choice = (self.load_choice + 1) % len(self.CARGO_CYCLE)

    @property
    def vision_range(self):
        return 1

    @property
    def total_weight(self):
        return sum(self.cargo[t] * config.CARGO_WEIGHT_PER_UNIT.get(t, 1) for t in self.CARGO_CYCLE)

    @property
    def weight_remaining(self):
        return self.max_weight - self.total_weight

    def get_movement_cost(self, terrain):
        cost = config.TERRAIN_MOVEMENT_COST.get(terrain, 1)
        if terrain == config.ROAD:
            cost *= 0.5  # Бонус 50% для техники на дороге
        return cost

    def load_by_weight(self, cargo_type, amount):
        wpu = config.CARGO_WEIGHT_PER_UNIT.get(cargo_type, 1)
        max_by_weight = self.weight_remaining // wpu
        taken = min(max_by_weight, amount)
        if taken > 0:
            self.cargo[cargo_type] = self.cargo.get(cargo_type, 0) + taken
        return taken

    def unload(self, supplies_type, amount):
        available = self.cargo.get(supplies_type, 0)
        given = min(available, amount)
        self.cargo[supplies_type] -= given
        return given

    def take_damage(self, amount):
        actual = max(1, amount)
        alive = self.alive_soldiers
        to_kill = min(len(alive), actual)
        for s in random.sample(alive, to_kill):
            s.is_alive = False
        if self.crew <= 0:
            self.die()

    def load_recon_drone_from_warehouse(self, warehouse):
        if not hasattr(warehouse, 'recon_drones'):
            return False
        if self.cargo.get(config.CARGO_RECON_DRONE, 0) >= 1:
            return False
        if warehouse.recon_drones <= 0:
            return False
        wpu = config.CARGO_WEIGHT_PER_UNIT.get(config.CARGO_RECON_DRONE, 20)
        if self.weight_remaining < wpu:
            return False
        warehouse.recon_drones -= 1
        self.cargo[config.CARGO_RECON_DRONE] = self.cargo.get(config.CARGO_RECON_DRONE, 0) + 1
        return True

    def unload_recon_drone_to_operator(self, operator):
        if not hasattr(operator, 'drone_stored'):
            return False
        if self.cargo.get(config.CARGO_RECON_DRONE, 0) <= 0:
            return False
        if operator.drone_stored >= operator.max_drone_stored:
            return False
        self.cargo[config.CARGO_RECON_DRONE] -= 1
        operator.drone_stored += 1
        return True

    def load_fpv_drone_from_warehouse(self, warehouse):
        if not hasattr(warehouse, 'fpv_drones'):
            return False
        if warehouse.fpv_drones <= 0:
            return False
        wpu = config.CARGO_WEIGHT_PER_UNIT.get(config.CARGO_FPV_DRONE, 15)
        max_by_weight = self.weight_remaining // wpu
        if max_by_weight <= 0:
            return False
        taken = min(max_by_weight, 5, warehouse.fpv_drones)
        warehouse.fpv_drones -= taken
        self.cargo[config.CARGO_FPV_DRONE] = self.cargo.get(config.CARGO_FPV_DRONE, 0) + taken
        return True

    def unload_fpv_drone_to_operator(self, operator):
        if not hasattr(operator, 'fpv_stock'):
            return False
        available = self.cargo.get(config.CARGO_FPV_DRONE, 0)
        if available <= 0:
            return False
        need = operator.max_stock - operator.fpv_stock
        if need <= 0:
            return False
        give = min(available, need)
        self.cargo[config.CARGO_FPV_DRONE] -= give
        operator.fpv_stock += give
        return True

    def status_lines(self):
        lines = [f"Топливо: {self.fuel}/{self.max_fuel}", f"Вес: {self.total_weight}/{self.max_weight}"]
        for k, v in self.cargo.items():
            if v > 0:
                lines.append(f"{config.CARGO_NAMES.get(k, k)}: {v}")
        if self.auto_mix:
            lines.append("Режим: всё подряд (V-переключить)")
        else:
            lines.append(f"Груз: {config.CARGO_NAMES.get(self.current_load_type, self.current_load_type)} (V-сменить)")
        if self.supply_route:
            origin = self.supply_route["origin"]
            dest = self.supply_route["dest"]
            o_name = origin.name if hasattr(origin, 'name') else str(origin.x)
            d_name = dest.name if hasattr(dest, 'name') else str(dest.x)
            lines.append(f"Маршрут: {o_name} -> {d_name}")
            state_names = {"to_origin": "едет на склад", "to_dest": "едет к погребу", "loading": "загрузка", "loaded": "в пути"}
            lines.append(f"Статус: {state_names.get(self.supply_route['state'], self.supply_route['state'])}")
        else:
            if self._route_origin:
                lines.append(f"Склад: {self._route_origin.name}")
            if self._route_dest:
                lines.append(f"Погреб: {self._route_dest.name}")
        return lines


class Warehouse:
    def __init__(self, x, y, faction, name="Склад"):
        self.x = x
        self.y = y
        self.faction = faction
        self.name = name
        self.supplies = 80
        self.max_supplies = 200
        self.ammo = 60
        self.max_ammo = 150
        self.fuel = 40
        self.max_fuel = 100
        self.batteries = 30
        self.max_batteries = 80
        self.fpv_drones = 5
        self.recon_drones = 3
        self.alive = True
        self.stationary_turns = 0
        self.moved = False
        self.attacked = False
        self.entrenching = False
        self.color = (50, 180, 180) if faction == config.PLAYER else (180, 50, 180)

    @property
    def vision_range(self):
        return 2

    @property
    def is_alive(self):
        return self.alive

    @property
    def type(self):
        return config.WAREHOUSE

    def die(self):
        self.alive = False

    def reinforce(self):
        self.supplies = min(self.max_supplies, self.supplies + 40)
        self.ammo = min(self.max_ammo, self.ammo + 30)
        self.fuel = min(self.max_fuel, self.fuel + 20)
        self.batteries = min(self.max_batteries, self.batteries + 15)
        self.recon_drones = min(5, self.recon_drones + 1)

    def reset_turn(self):
        pass

    def status_lines(self):
        return [
            f"Припасы: {self.supplies}",
            f"Боезапас: {self.ammo}",
            f"Топливо: {self.fuel}",
            f"Батареи: {self.batteries}",
            f"FPV: {self.fpv_drones}",
            f"Разведдроны: {self.recon_drones}",
        ]


class ReconOperator(Unit):
    def __init__(self, x, y, faction, name="Оператор дронов"):
        super().__init__(x, y, "recon_operator", faction, name)
        self.batteries = 30
        self.max_batteries = 30
        self.food = config.RECON_OPERATOR_MAX_FOOD
        self.max_food = config.RECON_OPERATOR_MAX_FOOD
        self.ammo = config.RECON_OPERATOR_MAX_AMMO
        self.max_ammo = config.RECON_OPERATOR_MAX_AMMO
        self.morale = 100
        self.drone_slot = None
        self.drone = None
        self.drone_stored = 1
        self.max_drone_stored = 1
        self.color = (50, 180, 200) if faction == config.PLAYER else (200, 100, 50)
        self.max_soldiers = config.RECON_OPERATOR_MAX_CREW
        self.min_crew = config.RECON_OPERATOR_MIN_CREW
        self.soldiers_list = self._generate_crew(config.RECON_OPERATOR_INIT_CREW)
        self.turns_without_food = 0

    @property
    def crew(self):
        return len([s for s in self.soldiers_list if s.is_alive])

    @property
    def alive_soldiers(self):
        return [s for s in self.soldiers_list if s.is_alive]

    @property
    def is_understaffed(self):
        return len(self.alive_soldiers) < self.min_crew

    def add_soldier(self, soldier):
        if len(self.alive_soldiers) < self.max_soldiers:
            self.soldiers_list.append(soldier)
            return True
        return False

    def remove_soldier(self, soldier):
        if soldier in self.soldiers_list:
            self.soldiers_list.remove(soldier)
            return True
        return False

    def transfer_soldier(self, soldier, target_unit):
        if not hasattr(target_unit, 'add_soldier'):
            return False
        if len(target_unit.alive_soldiers) >= target_unit.max_soldiers:
            return False
        if self.remove_soldier(soldier):
            target_unit.add_soldier(soldier)
            return True
        return False

    @property
    def is_radar_source(self):
        return True

    @property
    def vision_range(self):
        return 2

    def take_damage(self, amount):
        self.die()

    def has_batteries(self):
        return self.batteries > 0

    def give_battery(self):
        if self.batteries > 0:
            self.batteries -= 1
            return True
        return False

    def recharge_drone(self, drone):
        if not drone.is_alive:
            return False
        if abs(self.x - drone.x) + abs(self.y - drone.y) > 1:
            return False
        if self.batteries <= 0:
            return False
        given = 0
        while drone.battery < drone.max_battery and self.batteries > 0:
            drone.battery += 1
            self.batteries -= 1
            given += 1
        drone.can_fpv_strike = True
        return given > 0

    def load_batteries_from_warehouse(self, warehouse):
        if hasattr(warehouse, 'batteries') and warehouse.batteries > 0:
            need = self.max_batteries - self.batteries
            taken = min(need, warehouse.batteries)
            self.batteries += taken
            warehouse.batteries -= taken
            return taken
        return 0

    def consume_food(self):
        """Consume food every FOOD_CONSUMPTION_INTERVAL turns"""
        n = self.crew
        food_cost = max(1, n)
        self.food -= food_cost
        # Also consume each soldier's personal food
        for s in self.alive_soldiers:
            s.consume_food()
        if self.food <= 0:
            self.turns_without_food += 1
            if self.turns_without_food >= 2:
                self.morale = max(0, self.morale - 10)
        else:
            self.turns_without_food = 0

    def status_lines(self):
        drone_status = "Связан" if (self.drone and self.drone.is_alive) else "Нет"
        return [
            f"Дроны в запасе: {self.drone_stored}/{self.max_drone_stored}",
            f"Активный дрон: {drone_status}",
            f"Батареи: {self.batteries}/{self.max_batteries}",
            f"Еда: {self.food}/{self.max_food}",
            f"Боезапас: {self.ammo}/{self.max_ammo}",
            f"Мораль: {self.morale}%",
        ]

    def deploy_drone(self, game):
        if self.drone_stored <= 0:
            return None, "Нет дрона в запасе"
        if self.drone and self.drone.is_alive:
            return None, "Дрон уже активен"
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < game.map.width and 0 <= ny < game.map.height:
                cell = game.map.get_cell(nx, ny)
                if cell and cell.is_walkable and cell.terrain != config.RIVER:
                    self.drone_stored -= 1
                    drone = ReconDrone(nx, ny, self.faction, f"Дрон-{self.name}")
                    game.all_units.append(drone)
                    if self.faction == config.PLAYER:
                        game.player_units.append(drone)
                    else:
                        game.enemy_units.append(drone)
                    game.map.add_unit(drone, nx, ny)
                    self.link_drone(drone)
                    return drone, "Дрон развёрнут"
        return None, "Нет свободной клетки рядом"

    def load_drone_from_warehouse(self, warehouse):
        if not hasattr(warehouse, 'recon_drones'):
            return False
        if self.drone_stored >= self.max_drone_stored:
            return False
        if warehouse.recon_drones <= 0:
            return False
        warehouse.recon_drones -= 1
        self.drone_stored += 1
        return True

    def load_drone_from_truck(self, truck):
        if not hasattr(truck, 'cargo'):
            return False
        if self.drone_stored >= self.max_drone_stored:
            return False
        if truck.cargo.get(config.CARGO_RECON_DRONE, 0) <= 0:
            return False
        truck.cargo[config.CARGO_RECON_DRONE] -= 1
        self.drone_stored += 1
        return True

    def link_drone(self, drone):
        if self.drone:
            self.drone.operator = None
        self.drone = drone
        drone.operator = self
        return True

    def unlink_drone(self):
        if self.drone:
            self.drone.operator = None
            self.drone = None


class SupplyCache:
    CARGO_TYPES = [config.CARGO_SUPPLIES, config.CARGO_AMMO, config.CARGO_FUEL, config.CARGO_BATTERIES]

    def __init__(self, x, y, faction, name="Погреб"):
        self.x = x
        self.y = y
        self.faction = faction
        self.name = name
        self.supplies = 0
        self.max_supplies = 200
        self.ammo = 0
        self.max_ammo = 100
        self.fuel = 0
        self.max_fuel = 60
        self.batteries = 0
        self.max_batteries = 30
        self.max_slots = 30
        self.fpv_drones = 0
        self.recon_drones = 0
        self.alive = True
        self.moved = False
        self.attacked = False
        self.stationary_turns = 0
        self.build_turns = 0
        self.build_required = 5
        self.color = (150, 120, 60) if faction == config.PLAYER else (180, 100, 50)
        self.garrison = 0
        self.reserve_soldiers = []

    @property
    def vision_range(self):
        return 1

    @property
    def is_alive(self):
        return self.alive

    @property
    def type(self):
        return "supply_cache"

    def die(self):
        self.alive = False

    def reset_turn(self):
        pass

    def get_movement_cost(self, terrain):
        return 999  # Погреба не двигаются

    @property
    def used_slots(self):
        return self.supplies + self.ammo + self.fuel + self.batteries

    @property
    def slots_remaining(self):
        return max(0, self.max_slots - self.used_slots)

    def status_lines(self):
        if self.build_turns < self.build_required:
            return [f"Строительство: {self.build_turns}/{self.build_required} ходов"]
        lines = [
            f"Припасы: {self.supplies}",
            f"Боезапас: {self.ammo}",
            f"Топливо: {self.fuel}",
            f"Батареи: {self.batteries}",
            f"FPV: {self.fpv_drones}",
            f"Разведдроны: {self.recon_drones}",
        ]
        if self.garrison > 0:
            lines.append(f"Гарнизон: {self.garrison} отряд(ов) (G-выйти)")
        if self.reserve_soldiers:
            lines.append(f"Резерв: {len(self.reserve_soldiers)} чел.")
        lines.append(f"Места: {self.used_slots}/{self.max_slots}")
        return lines

    def add_to_reserve(self, soldier):
        self.reserve_soldiers.append(soldier)

    def take_from_reserve(self):
        if self.reserve_soldiers:
            return self.reserve_soldiers.pop()
        return None
