import random
from . import config
from .units import Infantry, Tank, SupplyCache, WOUND_NONE


# Типы анимаций боя
COMBAT_ANIM_INFANTRY_FIGHT = "infantry_fight"    # Перестрелка пехоты
COMBAT_ANIM_TANK_DUEL = "tank_duel"              # Танковый дуэль
COMBAT_ANIM_TANK_VS_INF = "tank_vs_infantry"     # Танк против пехоты
COMBAT_ANIM_ARTILLERY = "artillery_strike"        # Артиллерийский удар
COMBAT_ANIM_FPV = "fpv_strike"                   # FPV удар


def resolve_attack(attacker, defender, game_map=None):
    """Основная функция разрешения атаки с анимацией"""
    if not attacker.is_alive or not defender.is_alive:
        return None

    if isinstance(attacker, Infantry) and isinstance(defender, Infantry):
        return resolve_infantry_vs_infantry(attacker, defender, game_map)
    elif isinstance(attacker, Tank) and isinstance(defender, Tank):
        return resolve_tank_vs_tank(attacker, defender)
    elif isinstance(attacker, Tank) and isinstance(defender, Infantry):
        return resolve_tank_vs_infantry(attacker, defender)
    elif isinstance(attacker, Infantry) and isinstance(defender, Tank):
        return resolve_infantry_vs_tank(attacker, defender, game_map)
    elif isinstance(attacker, Tank):
        return resolve_tank_attack(attacker, defender)
    elif isinstance(defender, (SupplyCache, Warehouse)):
        return resolve_vs_structure(attacker, defender)
    return None


def resolve_infantry_vs_infantry(attacker, defender, game_map=None):
    """Бой пехота против пехоты с детальной анимацией"""
    total_ammo_attacker = sum(s.ammo for s in attacker.alive_soldiers)
    total_ammo_defender = sum(s.ammo for s in defender.alive_soldiers)
    
    if total_ammo_attacker <= 0:
        return {
            "attacker": attacker,
            "defender": defender,
            "damage": 0,
            "counter_damage": 0,
            "message": f"{attacker.name}: нет боезапаса!",
            "defender_alive": defender.is_alive,
            "attacker_alive": attacker.is_alive,
            "animation": COMBAT_ANIM_INFANTRY_FIGHT,
            "hits": [],
            "wounds_inflicted": 0,
        }
    
    # Расход боеприпасов обеими сторонами
    for s in attacker.alive_soldiers:
        if s.ammo > 0:
            s.ammo -= 1
            break
    
    # Определяем количество выстрелов (зависит от численности)
    num_shots = min(len(attacker.alive_soldiers), 3)
    hits = []
    total_damage = 0
    wounds_inflicted = 0
    
    for _ in range(num_shots):
        if random.randint(1, 100) <= attacker.hit_chance:
            # Попадание
            dmg = max(1, attacker.attack_power // num_shots)
            # Учитываем укрепление клетки защитника
            if game_map:
                def_cell = game_map.get_cell(defender.x, defender.y)
                dmg = max(1, dmg - def_cell.entrenchment // 30)
            
            # Наносим урон случайному солдату
            alive = defender.alive_soldiers
            if alive:
                target_soldier = random.choice(alive)
                target_soldier.take_damage(dmg * 20)  # Урон в процентах здоровья
                
                # Определяем уровень ранения
                if target_soldier.wound_level > WOUND_NONE:
                    wounds_inflicted += 1
                
                hits.append({
                    "x": defender.x + random.uniform(-0.3, 0.3),
                    "y": defender.y + random.uniform(-0.3, 0.3),
                    "damage": dmg,
                    "wound": target_soldier.wound_level,
                })
                total_damage += dmg
                
                if not target_soldier.is_alive:
                    hits[-1]["kill"] = True
    
    # Контратака защитника
    counter_damage = 0
    if total_ammo_defender > 0 and defender.is_alive and total_damage > 0:
        for s in defender.alive_soldiers:
            if s.ammo > 0:
                s.ammo -= 1
                break
        
        if random.randint(1, 100) <= defender.hit_chance:
            counter_dmg = max(1, defender.attack_power // 2)
            # Учитываем укрепление клетки атакующего
            if game_map:
                atk_cell = game_map.get_cell(attacker.x, attacker.y)
                counter_dmg = max(1, counter_dmg - atk_cell.entrenchment // 30)
            
            alive = attacker.alive_soldiers
            if alive:
                target = random.choice(alive)
                target.take_damage(counter_dmg * 20)
                counter_damage = counter_dmg
                
                hits.append({
                    "x": attacker.x + random.uniform(-0.3, 0.3),
                    "y": attacker.y + random.uniform(-0.3, 0.3),
                    "damage": counter_dmg,
                    "counter": True,
                    "wound": target.wound_level,
                })
    
    # Формируем сообщение
    if total_damage > 0:
        msg = f"{attacker.name} -> {defender.name}: {total_damage} урона"
        if wounds_inflicted > 0:
            msg += f" ({wounds_inflicted} ранен)"
        if counter_damage > 0:
            msg += f" | Контратака: {counter_damage}"
    else:
        msg = f"{attacker.name} -> {defender.name}: промах!"
    
    return {
        "attacker": attacker,
        "defender": defender,
        "damage": total_damage,
        "counter_damage": counter_damage,
        "message": msg,
        "defender_alive": defender.is_alive,
        "attacker_alive": attacker.is_alive,
        "animation": COMBAT_ANIM_INFANTRY_FIGHT,
        "hits": hits,
        "wounds_inflicted": wounds_inflicted,
    }


def resolve_tank_vs_tank(attacker, defender):
    """Танковый дуэль с эффектами рикошетов и взрывов"""
    if attacker.ammo <= 0:
        return {
            "attacker": attacker,
            "defender": defender,
            "damage": 0,
            "counter_damage": 0,
            "message": f"{attacker.name}: нет снарядов!",
            "defender_alive": defender.is_alive,
            "attacker_alive": attacker.is_alive,
            "animation": COMBAT_ANIM_TANK_DUEL,
            "hits": [],
            "ricochet": False,
        }
    
    attacker.ammo -= 1
    hits = []
    ricochet = False
    total_damage = 0
    counter_damage = 0
    
    # Выстрел атакующего
    if random.randint(1, 100) <= attacker.hit_chance:
        # Проверка на рикошет (30% шанс для танка против танка)
        if random.randint(1, 100) <= 30:
            ricochet = True
            hits.append({
                "x": defender.x + random.uniform(-0.2, 0.2),
                "y": defender.y + random.uniform(-0.2, 0.2),
                "damage": 0,
                "ricochet": True,
            })
        else:
            # Пробитие брони
            dmg = attacker.attack_power
            # Учитываем броню защитника
            armor_absorb = min(dmg, defender.armor // 15)
            actual_dmg = max(1, dmg - armor_absorb)
            
            defender.take_damage(actual_dmg)
            total_damage = actual_dmg
            
            hits.append({
                "x": defender.x + random.uniform(-0.2, 0.2),
                "y": defender.y + random.uniform(-0.2, 0.2),
                "damage": actual_dmg,
                "explosion": True,
            })
            
            # Урон экипажу
            if random.randint(1, 100) <= 40:
                crew_alive = defender.alive_soldiers
                if crew_alive:
                    crew_target = random.choice(crew_alive)
                    crew_damage = random.randint(10, 30)
                    crew_target.take_damage(crew_damage)
                    hits[-1]["crew_damage"] = crew_damage
    else:
        hits.append({
            "x": defender.x + random.uniform(-0.5, 0.5),
            "y": defender.y + random.uniform(-0.5, 0.5),
            "damage": 0,
            "miss": True,
        })
    
    # Контратака защитника
    if defender.is_alive and defender.ammo > 0:
        defender.ammo -= 1
        if random.randint(1, 100) <= defender.hit_chance:
            if random.randint(1, 100) <= 30:
                # Рикошет защитника
                hits.append({
                    "x": attacker.x + random.uniform(-0.2, 0.2),
                    "y": attacker.y + random.uniform(-0.2, 0.2),
                    "damage": 0,
                    "ricochet": True,
                    "counter": True,
                })
            else:
                counter_dmg = defender.attack_power
                armor_absorb = min(counter_dmg, attacker.armor // 15)
                actual_counter = max(1, counter_dmg - armor_absorb)
                
                attacker.take_damage(actual_counter)
                counter_damage = actual_counter
                
                hits.append({
                    "x": attacker.x + random.uniform(-0.2, 0.2),
                    "y": attacker.y + random.uniform(-0.2, 0.2),
                    "damage": actual_counter,
                    "explosion": True,
                    "counter": True,
                })
    
    # Формируем сообщение
    if ricochet:
        msg = f"{attacker.name} -> {defender.name}: РИКОШЕТ!"
    elif total_damage > 0:
        msg = f"{attacker.name} -> {defender.name}: {total_damage} урона"
        if counter_damage > 0:
            msg += f" | Контратака: {counter_damage}"
    else:
        msg = f"{attacker.name} -> {defender.name}: промах!"
    
    return {
        "attacker": attacker,
        "defender": defender,
        "damage": total_damage,
        "counter_damage": counter_damage,
        "message": msg,
        "defender_alive": defender.is_alive,
        "attacker_alive": attacker.is_alive,
        "animation": COMBAT_ANIM_TANK_DUEL,
        "hits": hits,
        "ricochet": ricochet,
    }


def resolve_tank_vs_infantry(attacker, defender):
    """Танк против пехоты - стрельба картечью"""
    if attacker.ammo <= 0:
        return {
            "attacker": attacker,
            "defender": defender,
            "damage": 0,
            "counter_damage": 0,
            "message": f"{attacker.name}: нет снарядов!",
            "defender_alive": defender.is_alive,
            "attacker_alive": attacker.is_alive,
            "animation": COMBAT_ANIM_TANK_VS_INF,
            "hits": [],
        }
    
    attacker.ammo -= 1
    hits = []
    total_damage = 0
    
    # Танк стреляет картечью по пехоте
    num_targets = min(len(defender.alive_soldiers), attacker.attack_power + 2)
    
    if random.randint(1, 100) <= attacker.hit_chance:
        for _ in range(num_targets):
            alive = defender.alive_soldiers
            if not alive:
                break
            
            target = random.choice(alive)
            # Урон от картечи
            damage = random.randint(15, 40)
            target.take_damage(damage)
            total_damage += 1
            
            hits.append({
                "x": target.x if hasattr(target, 'x') else defender.x + random.uniform(-0.3, 0.3),
                "y": target.y if hasattr(target, 'y') else defender.y + random.uniform(-0.3, 0.3),
                "damage": 1,
                "kill": not target.is_alive,
            })
    else:
        hits.append({
            "x": defender.x + random.uniform(-0.5, 0.5),
            "y": defender.y + random.uniform(-0.5, 0.5),
            "damage": 0,
            "miss": True,
        })
    
    msg = f"{attacker.name} -> {defender.name}: {total_damage} потерь"
    
    return {
        "attacker": attacker,
        "defender": defender,
        "damage": total_damage,
        "counter_damage": 0,
        "message": msg,
        "defender_alive": defender.is_alive,
        "attacker_alive": attacker.is_alive,
        "animation": COMBAT_ANIM_TANK_VS_INF,
        "hits": hits,
    }


def resolve_infantry_vs_tank(attacker, defender, game_map=None):
    """Пехота против танка - гранатомёт/ПТРК"""
    if attacker.ammo <= 0:
        return {
            "attacker": attacker,
            "defender": defender,
            "damage": 0,
            "counter_damage": 0,
            "message": f"{attacker.name}: нет боезапаса!",
            "defender_alive": defender.is_alive,
            "attacker_alive": attacker.is_alive,
            "animation": COMBAT_ANIM_INFANTRY_FIGHT,
            "hits": [],
        }
    
    # Пехота тратит больше патронов на борьбу с танком
    ammo_cost = min(3, len([s for s in attacker.alive_soldiers if s.ammo > 0]))
    for _ in range(ammo_cost):
        for s in attacker.alive_soldiers:
            if s.ammo > 0:
                s.ammo -= 1
                break
    
    hits = []
    total_damage = 0
    
    # Шанс попадания из гранатомёта (30%)
    if random.randint(1, 100) <= 30:
        dmg = 1
        if isinstance(defender, Infantry):
            defender.take_damage(dmg, game_map)
        else:
            defender.take_damage(dmg)
        total_damage = dmg
        
        hits.append({
            "x": defender.x + random.uniform(-0.2, 0.2),
            "y": defender.y + random.uniform(-0.2, 0.2),
            "damage": dmg,
            "explosion": True,
        })
        
        msg = f"Гранатомёт! {defender.name} получил {dmg} урона"
    else:
        hits.append({
            "x": defender.x + random.uniform(-0.5, 0.5),
            "y": defender.y + random.uniform(-0.5, 0.5),
            "damage": 0,
            "miss": True,
        })
        msg = "Бесполезно! Броня слишком толстая"
    
    # Контратака танка по пехоте
    counter_damage = 0
    if defender.is_alive and defender.ammo > 0:
        defender.ammo -= 1
        if random.randint(1, 100) <= defender.hit_chance:
            alive = attacker.alive_soldiers
            if alive:
                num_kill = min(len(alive), defender.attack_power)
                for _ in range(num_kill):
                    if alive:
                        target = random.choice(alive)
                        target.take_damage(100)  # Убивает солдата
                        counter_damage += 1
                        alive.remove(target)
                        
                        hits.append({
                            "x": attacker.x + random.uniform(-0.3, 0.3),
                            "y": attacker.y + random.uniform(-0.3, 0.3),
                            "damage": 1,
                            "kill": True,
                            "counter": True,
                        })
    
    if counter_damage > 0:
        msg += f" | Контратака: {counter_damage} потерь"
    
    return {
        "attacker": attacker,
        "defender": defender,
        "damage": total_damage,
        "counter_damage": counter_damage,
        "message": msg,
        "defender_alive": defender.is_alive,
        "attacker_alive": attacker.is_alive,
        "animation": COMBAT_ANIM_INFANTRY_FIGHT,
        "hits": hits,
    }


def resolve_vs_structure(attacker, defender):
    """Атака на строение (склад/погреб)"""
    if not attacker.is_alive or not defender.is_alive:
        return None
    dmg = attacker.attack_power if hasattr(attacker, 'attack_power') else 3
    defender.die()
    return {
        "attacker": attacker,
        "defender": defender,
        "damage": dmg,
        "counter_damage": 0,
        "message": f"{attacker.name} уничтожил {defender.name}!",
        "defender_alive": False,
        "attacker_alive": attacker.is_alive,
        "animation": COMBAT_ANIM_INFANTRY_FIGHT,
        "hits": [{
            "x": defender.x,
            "y": defender.y,
            "damage": dmg,
            "explosion": True,
        }],
    }


def resolve_tank_attack(attacker, defender):
    """Общая атака танка"""
    dmg, msg = attacker.attack(defender)
    return {
        "attacker": attacker,
        "defender": defender,
        "damage": dmg,
        "counter_damage": 0,
        "message": f"{attacker.name} -> {defender.name}: {dmg} урона ({msg})",
        "defender_alive": defender.is_alive,
        "attacker_alive": attacker.is_alive,
        "animation": COMBAT_ANIM_TANK_DUEL,
        "hits": [{
            "x": defender.x,
            "y": defender.y,
            "damage": dmg,
            "explosion": dmg > 0,
        }],
    }


def resolve_fpv_strike(drone, target, warehouse, game_map=None):
    """FPV удар"""
    if not drone.can_fpv_strike:
        return None
    if warehouse.fpv_drones <= 0:
        return None

    warehouse.fpv_drones -= 1
    entrench = 0
    if game_map:
        cell = game_map.get_cell(target.x, target.y)
        entrench = cell.entrenchment
    hit_chance = config.FPV_HIT_CHANCE_BASE * (1 - entrench / 100)
    hit = random.random() <= hit_chance

    if not hit:
        return {
            "drone": drone,
            "target": target,
            "hit": False,
            "damage": 0,
            "message": f"FPV промахнулся по {target.name}!",
            "animation": COMBAT_ANIM_FPV,
            "hits": [{
                "x": target.x + random.uniform(-1, 1),
                "y": target.y + random.uniform(-1, 1),
                "damage": 0,
                "miss": True,
            }],
        }

    if isinstance(target, Infantry):
        dmg = target.take_fpv_damage(game_map)
    elif isinstance(target, Tank):
        dmg = config.FPV_DAMAGE_ARMOR
        target.take_damage(dmg)
    else:
        target.die()
        dmg = 99

    return {
        "drone": drone,
        "target": target,
        "hit": True,
        "damage": dmg,
        "message": f"FPV поразил {target.name}! Урон: {dmg}",
        "animation": COMBAT_ANIM_FPV,
        "hits": [{
            "x": target.x,
            "y": target.y,
            "damage": dmg,
            "explosion": True,
        }],
    }
