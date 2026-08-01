from . import config
from .units import (
    Infantry, Tank, ReconDrone, SupplyTruck, Warehouse,
    FPVOperator, ReconOperator, SupplyCache, Artillery, SoldierUnit, RadarEW,
)


# ─── helpers (small reusable pieces of transfer logic) ────────────────

def _soldiers_give_to_soldiers(src_soldiers, tgt_soldiers, res_type, limit):
    """Transfer a resource from source soldiers to target soldiers.
    Used when both sides have alive_soldiers with personal food/ammo.
    Returns total transferred.
    """
    total = 0
    attr = "food" if res_type == "food" else "ammo"
    max_attr = f"max_{attr}"
    for s in src_soldiers:
        src_val = getattr(s, attr)
        if src_val <= 0:
            continue
        for ts in tgt_soldiers:
            ts_val = getattr(ts, attr)
            ts_max = getattr(ts, max_attr)
            if ts_val >= ts_max:
                continue
            give = min(limit - total, src_val, ts_max - ts_val)
            if give <= 0:
                break
            setattr(s, attr, src_val - give)
            setattr(ts, attr, ts_val + give)
            total += give
            src_val -= give
        if total >= limit:
            break
    return total


def _stockpile_give_to_soldiers(source, tgt_soldiers, res_type, source_attr, limit):
    """Transfer from a scalar stockpile (source.supplies / source.ammo / …)
    into target soldiers' personal reserves.
    Returns total transferred.
    """
    total = 0
    attr = "food" if res_type == "food" else "ammo"
    max_attr = f"max_{attr}"
    stock = getattr(source, source_attr, 0)
    for ts in tgt_soldiers:
        if stock <= 0:
            break
        ts_val = getattr(ts, attr)
        ts_max = getattr(ts, max_attr)
        if ts_val >= ts_max:
            continue
        give = min(limit, stock, ts_max - ts_val)
        setattr(ts, attr, ts_val + give)
        stock -= give
        total += give
    setattr(source, source_attr, stock)
    return total


def _scalar_give(source, target, res_type, src_attr, tgt_attr, tgt_max_attr, limit):
    """Transfer a scalar resource between two units.
    Returns amount transferred.
    """
    src_val = getattr(source, src_attr, 0)
    if src_val <= 0:
        return 0
    tgt_val = getattr(target, tgt_attr, 0)
    tgt_max = getattr(target, tgt_max_attr, 0)
    if tgt_val >= tgt_max:
        return 0
    give = min(limit, src_val, tgt_max - tgt_val)
    setattr(source, src_attr, src_val - give)
    setattr(target, tgt_attr, tgt_val + give)
    return give


# ─── individual transfer handlers ─────────────────────────────────────

def _infantry_to_infantry(src, tgt, res_type, limit):
    if res_type == "food":
        return _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "food", limit)
    elif res_type == "ammo":
        return _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "ammo", limit)
    return 0


def _infantry_to_tank(src, tgt, res_type, limit):
    total = 0
    if res_type == "ammo":
        total = _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "ammo", limit)
    elif res_type == "food":
        total = _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "food", limit)
    return total


def _infantry_to_soldier_unit(src, tgt, res_type, limit):
    attr = "food" if res_type == "food" else "ammo"
    max_attr = f"max_{attr}"
    for s in src.alive_soldiers:
        sv = getattr(s, attr)
        if sv <= 0:
            continue
        tv = getattr(tgt.soldier, attr)
        tm = getattr(tgt.soldier, max_attr)
        if tv >= tm:
            continue
        give = min(limit, sv, tm - tv)
        setattr(s, attr, sv - give)
        setattr(tgt.soldier, attr, tv + give)
        return give
    return 0


def _infantry_to_truck(src, tgt, res_type, limit):
    """Infantry dumps resources into truck (no target capacity check)."""
    total = 0
    if res_type == "food":
        for s in src.alive_soldiers:
            if s.food <= 0:
                continue
            give = min(s.food, limit - total)
            s.food -= give
            total += give
            if total >= limit:
                break
    elif res_type == "ammo":
        for s in src.alive_soldiers:
            if s.ammo <= 0:
                continue
            give = min(s.ammo, limit - total)
            s.ammo -= give
            total += give
            if total >= limit:
                break
    return total


def _tank_to_infantry(src, tgt, res_type, limit):
    if res_type == "food":
        total = 0
        if src.carry_food > 0:
            for ts in tgt.alive_soldiers:
                if src.carry_food <= 0:
                    break
                if ts.food >= ts.max_food:
                    continue
                give = min(limit - total, src.carry_food, ts.max_food - ts.food)
                src.carry_food -= give
                ts.food += give
                total += give
                if total >= limit:
                    break
        if total < limit:
            extra = _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "food", limit - total)
            total += extra
        return total
    elif res_type == "ammo":
        return _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "ammo", limit)
    return 0


def _tank_to_tank(src, tgt, res_type, limit):
    if res_type == "ammo":
        return _soldiers_give_to_soldiers(src.alive_soldiers, tgt.alive_soldiers, "ammo", limit)
    elif res_type == "fuel":
        return _scalar_give(src, tgt, "fuel", "fuel", "fuel", "max_fuel", limit)
    return 0


def _warehouse_to_infantry(src, tgt, res_type, limit):
    if res_type == "food":
        return _stockpile_give_to_soldiers(src, tgt.alive_soldiers, "food", "supplies", limit)
    elif res_type == "ammo":
        return _stockpile_give_to_soldiers(src, tgt.alive_soldiers, "ammo", "ammo", limit)
    return 0


def _warehouse_to_tank(src, tgt, res_type, limit):
    total = 0
    if res_type == "ammo":
        total = _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", min(limit, config.TRANSFER_WAREHOUSE_TO_TANK_LIMIT))
    elif res_type == "fuel":
        total = _scalar_give(src, tgt, "fuel", "fuel", "fuel", "max_fuel", min(limit, config.TRANSFER_WAREHOUSE_TO_TANK_LIMIT))
    elif res_type == "food":
        total = _scalar_give(src, tgt, "food", "supplies", "carry_food", "max_carry_food", min(limit, config.TRANSFER_WAREHOUSE_TO_TANK_LIMIT))
        if total < limit:
            extra = _stockpile_give_to_soldiers(src, tgt.alive_soldiers, "food", "supplies", limit - total)
            total += extra
    return total


def _warehouse_to_artillery(src, tgt, res_type, limit):
    total = 0
    if res_type == "ammo":
        total = _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", min(limit, config.TRANSFER_WAREHOUSE_TO_ARTILLERY_LIMIT))
    elif res_type == "food":
        total = _stockpile_give_to_soldiers(src, tgt.alive_soldiers, "food", "supplies", limit)
    return total


def _warehouse_to_recon_op(src, tgt, res_type, limit):
    total = 0
    if res_type == "batteries":
        total = _scalar_give(src, tgt, "batteries", "batteries", "batteries", "max_batteries", min(limit, config.TRANSFER_WAREHOUSE_TO_RECON_BATTERY_LIMIT))
    elif res_type == "food":
        total = _scalar_give(src, tgt, "food", "supplies", "food", "max_food", limit)
    elif res_type == "ammo":
        total = _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", limit)
    return total


def _warehouse_to_fpv_op(src, tgt, res_type, limit):
    total = 0
    if res_type == "fpv":
        total = _scalar_give(src, tgt, "fpv", "fpv_drones", "fpv_stock", "max_stock", min(limit, config.TRANSFER_WAREHOUSE_TO_FPV_DRONE_LIMIT))
    elif res_type == "ammo":
        total = _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", min(limit, config.TRANSFER_WAREHOUSE_TO_FPV_AMMO_LIMIT))
    elif res_type == "food":
        total = _scalar_give(src, tgt, "food", "supplies", "food", "max_food", limit)
    return total


def _warehouse_to_truck(src, tgt, res_type, limit):
    """Warehouse/Cache loads cargo into truck by weight."""
    cargo_map = {
        "food": "supplies", "ammo": "ammo", "fuel": "fuel", "batteries": "batteries",
    }
    src_attr = cargo_map.get(res_type)
    if not src_attr:
        return 0
    available = getattr(src, src_attr, 0)
    if available <= 0:
        return 0
    wpu = config.CARGO_WEIGHT_PER_UNIT.get(res_type if res_type != "food" else config.CARGO_SUPPLIES, 1)
    max_load = min(available, tgt.weight_remaining // wpu, limit)
    if max_load <= 0:
        return 0
    cargo_key = {"food": config.CARGO_SUPPLIES, "ammo": config.CARGO_AMMO,
                 "fuel": config.CARGO_FUEL, "batteries": config.CARGO_BATTERIES}.get(res_type, res_type)
    taken = tgt.load_by_weight(cargo_key, max_load)
    setattr(src, src_attr, available - taken)
    return taken


def _truck_to_infantry(truck, tgt, res_type, limit):
    total = 0
    if res_type == "food":
        cargo_key = config.CARGO_SUPPLIES
        for s in tgt.alive_soldiers:
            if truck.cargo.get(cargo_key, 0) <= 0:
                break
            if s.food >= s.max_food:
                continue
            need = s.max_food - s.food
            given = truck.unload(cargo_key, min(need, limit))
            s.food += given
            total += given
    elif res_type == "ammo":
        cargo_key = config.CARGO_AMMO
        for s in tgt.alive_soldiers:
            if truck.cargo.get(cargo_key, 0) <= 0:
                break
            if s.ammo >= s.max_ammo:
                continue
            need = s.max_ammo - s.ammo
            given = truck.unload(cargo_key, min(need, limit))
            s.ammo += given
            total += given
    return total


def _truck_to_tank(truck, tgt, res_type, limit):
    total = 0
    if res_type == "ammo" and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
        need = tgt.max_ammo - tgt.ammo
        given = truck.unload(config.CARGO_AMMO, min(need, config.TRANSFER_TRUCK_TO_TANK_AMMO_LIMIT))
        tgt.ammo += given
        total += given
    elif res_type == "fuel" and truck.cargo.get(config.CARGO_FUEL, 0) > 0:
        need = tgt.max_fuel - tgt.fuel
        given = truck.unload(config.CARGO_FUEL, min(need, config.TRANSFER_TRUCK_TO_TANK_FUEL_LIMIT))
        tgt.fuel += given
        total += given
    elif res_type == "food" and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
        need = tgt.max_carry_food - tgt.carry_food
        given = truck.unload(config.CARGO_SUPPLIES, min(need, config.TRANSFER_TRUCK_TO_TANK_FOOD_LIMIT))
        tgt.carry_food += given
        total += given
    return total


def _truck_to_recon_op(truck, tgt, res_type, limit):
    total = 0
    if res_type == "batteries" and truck.cargo.get(config.CARGO_BATTERIES, 0) > 0:
        need = tgt.max_batteries - tgt.batteries
        given = truck.unload(config.CARGO_BATTERIES, min(need, config.TRANSFER_TRUCK_TO_RECON_BATTERY_LIMIT))
        tgt.batteries += given
        total += given
    elif res_type == "food" and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
        need = tgt.max_food - tgt.food
        given = truck.unload(config.CARGO_SUPPLIES, min(need, config.TRANSFER_TRUCK_TO_RECON_FOOD_AMMO_LIMIT))
        tgt.food += given
        total += given
    elif res_type == "ammo" and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
        need = tgt.max_ammo - tgt.ammo
        given = truck.unload(config.CARGO_AMMO, min(need, config.TRANSFER_TRUCK_TO_RECON_FOOD_AMMO_LIMIT))
        tgt.ammo += given
        total += given
    return total


def _truck_to_fpv_op(truck, tgt, res_type, limit):
    total = 0
    if res_type == "food" and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
        need = tgt.max_food - tgt.food
        given = truck.unload(config.CARGO_SUPPLIES, min(need, config.TRANSFER_TRUCK_TO_FPV_FOOD_AMMO_LIMIT))
        tgt.food += given
        total += given
    elif res_type == "ammo" and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
        need = tgt.max_ammo - tgt.ammo
        given = truck.unload(config.CARGO_AMMO, min(need, config.TRANSFER_TRUCK_TO_FPV_FOOD_AMMO_LIMIT))
        tgt.ammo += given
        total += given
    return total


def _truck_to_soldier_unit(truck, tgt, res_type, limit):
    total = 0
    if res_type == "food" and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
        need = tgt.soldier.max_food - tgt.soldier.food
        given = truck.unload(config.CARGO_SUPPLIES, min(need, config.TRANSFER_TRUCK_TO_SOLDIER_FOOD_AMMO_LIMIT))
        tgt.soldier.food += given
        total += given
    elif res_type == "ammo" and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
        need = tgt.soldier.max_ammo - tgt.soldier.ammo
        given = truck.unload(config.CARGO_AMMO, min(need, config.TRANSFER_TRUCK_TO_SOLDIER_FOOD_AMMO_LIMIT))
        tgt.soldier.ammo += given
        total += given
    return total


def _truck_to_truck(truck, tgt, res_type, limit):
    if res_type == "fuel" and truck.cargo.get(config.CARGO_FUEL, 0) > 0:
        need = tgt.max_fuel - tgt.fuel
        given = truck.unload(config.CARGO_FUEL, min(need, config.TRANSFER_TRUCK_TO_TRUCK_FUEL_LIMIT))
        tgt.fuel += given
        return given
    return 0


def _truck_to_artillery(truck, tgt, res_type, limit):
    total = 0
    if res_type == "ammo" and truck.cargo.get(config.CARGO_AMMO, 0) > 0:
        need = tgt.max_ammo - tgt.ammo
        given = truck.unload(config.CARGO_AMMO, min(need, config.TRANSFER_TRUCK_TO_ARTILLERY_LIMIT))
        tgt.ammo += given
        total += given
    elif res_type == "food" and truck.cargo.get(config.CARGO_SUPPLIES, 0) > 0:
        for s in tgt.alive_soldiers:
            if truck.cargo.get(config.CARGO_SUPPLIES, 0) <= 0:
                break
            if s.food >= s.max_food:
                continue
            need = s.max_food - s.food
            given = truck.unload(config.CARGO_SUPPLIES, min(need, config.TRANSFER_TRUCK_TO_ARTILLERY_LIMIT))
            s.food += given
            total += given
    return total


def _soldier_unit_to_infantry(src, tgt, res_type, limit):
    attr = "food" if res_type == "food" else "ammo"
    max_attr = f"max_{attr}"
    sv = getattr(src.soldier, attr)
    if sv <= 1:
        return 0
    total = 0
    for ts in tgt.alive_soldiers:
        tv = getattr(ts, attr)
        tm = getattr(ts, max_attr)
        if tv >= tm:
            continue
        transfer = min(sv - tv if sv > tv else 0, config.TRANSFER_SOLDIER_TO_INFANTRY_LIMIT)
        if transfer <= 0:
            continue
        setattr(src.soldier, attr, sv - transfer)
        setattr(ts, attr, tv + transfer)
        total += transfer
        sv -= transfer
    return total


def _soldier_unit_to_soldier_unit(src, tgt, res_type, limit):
    attr = "food" if res_type == "food" else "ammo"
    max_attr = f"max_{attr}"
    sv = getattr(src.soldier, attr)
    tv = getattr(tgt.soldier, attr)
    if sv <= 1 or sv <= tv:
        return 0
    transfer = min(sv - tv, config.TRANSFER_SOLDIER_TO_SOLDIER_LIMIT)
    setattr(src.soldier, attr, sv - transfer)
    setattr(tgt.soldier, attr, tv + transfer)
    return transfer


def _tank_to_soldier_unit(src, tgt, res_type, limit):
    """Tank → SoldierUnit: give from carry_food or ammo."""
    if res_type == "food":
        if src.carry_food > 0:
            give = min(src.carry_food, tgt.soldier.max_food - tgt.soldier.food)
            if give > 0:
                src.carry_food -= give
                tgt.soldier.food += give
                return give
        for s in src.alive_soldiers:
            if s.food > config.TRANSFER_TANK_SURPLUS_FOOD_THRESHOLD:
                give = min(s.food - config.TRANSFER_TANK_SURPLUS_FOOD_THRESHOLD, config.TRANSFER_TANK_SURPLUS_FOOD_LIMIT)
                tgt.soldier.food += give
                s.food -= give
                return give
    elif res_type == "ammo":
        if src.ammo > 0:
            give = min(src.ammo, tgt.soldier.max_ammo - tgt.soldier.ammo, config.TRANSFER_TANK_TO_SOLDIER_AMMO_LIMIT)
            if give > 0:
                src.ammo -= give
                tgt.soldier.ammo += give
                return give
    return 0


def _artillery_to_infantry(src, tgt, res_type, limit):
    if res_type == "food":
        total = 0
        for s in src.alive_soldiers:
            available = s.food - config.TRANSFER_ARTILLERY_SURPLUS_FOOD_THRESHOLD
            if available <= 0:
                continue
            for ts in tgt.alive_soldiers:
                if ts.food >= ts.max_food:
                    continue
                give = min(limit - total, available, ts.max_food - ts.food)
                s.food -= give
                ts.food += give
                total += give
                available -= give
                if total >= limit:
                    break
            if total >= limit:
                break
        return total
    elif res_type == "ammo":
        return _stockpile_give_to_soldiers(src, tgt.alive_soldiers, "ammo", "ammo", limit)
    return 0


def _artillery_to_tank(src, tgt, res_type, limit):
    if res_type == "food":
        total = 0
        for s in src.alive_soldiers:
            available = s.food - config.TRANSFER_ARTILLERY_SURPLUS_FOOD_THRESHOLD
            if available <= 0:
                continue
            for ts in tgt.alive_soldiers:
                if ts.food >= ts.max_food:
                    continue
                give = min(limit - total, available, ts.max_food - ts.food)
                s.food -= give
                ts.food += give
                total += give
                available -= give
                if total >= limit:
                    break
            if total >= limit:
                break
        return total
    elif res_type == "ammo":
        return _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", limit)
    return 0


def _artillery_to_artillery(src, tgt, res_type, limit):
    if res_type == "food":
        total = 0
        for s in src.alive_soldiers:
            available = s.food - 100
            if available <= 0:
                continue
            for ts in tgt.alive_soldiers:
                if ts.food >= ts.max_food:
                    continue
                give = min(limit - total, available, ts.max_food - ts.food)
                s.food -= give
                ts.food += give
                total += give
                available -= give
                if total >= limit:
                    break
            if total >= limit:
                break
        return total
    elif res_type == "ammo":
        return _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", limit)
    return 0


def _recon_op_to_drone(src, tgt, res_type, limit):
    if res_type == "batteries":
        return _scalar_give(src, tgt, "batteries", "batteries", "battery", "max_battery", limit)
    return 0


def _fpv_op_to_fpv_op(src, tgt, res_type, limit):
    if res_type == "fpv":
        return _scalar_give(src, tgt, "fpv", "fpv_stock", "fpv_stock", "max_stock", limit)
    return 0


def _warehouse_to_radar_ew(src, tgt, res_type, limit):
    total = 0
    if res_type == "fuel":
        total = _scalar_give(src, tgt, "fuel", "fuel", "fuel", "max_fuel", min(limit, 10))
    elif res_type == "food":
        total = _scalar_give(src, tgt, "food", "supplies", "food", "max_food", limit)
    elif res_type == "ammo":
        total = _scalar_give(src, tgt, "ammo", "ammo", "ammo", "max_ammo", limit)
    return total


def _warehouse_to_soldier_unit(src, tgt, res_type, limit):
    if res_type == "food":
        return _stockpile_give_to_soldiers(src, [tgt.soldier], "food", "supplies", limit)
    elif res_type == "ammo":
        return _stockpile_give_to_soldiers(src, [tgt.soldier], "ammo", "ammo", limit)
    return 0


# ─── dispatch table ───────────────────────────────────────────────────

_TRANSFER_TABLE = {
    # (source_type, target_type) → handler(source, target, res_type, limit) → int
    (Infantry, Infantry):        _infantry_to_infantry,
    (Infantry, Tank):            _infantry_to_tank,
    (Infantry, SoldierUnit):     _infantry_to_soldier_unit,
    (Infantry, SupplyTruck):     _infantry_to_truck,

    (Tank, Infantry):            _tank_to_infantry,
    (Tank, Tank):                _tank_to_tank,
    (Tank, SoldierUnit):         _tank_to_soldier_unit,

    (Warehouse, Infantry):       _warehouse_to_infantry,
    (Warehouse, Tank):           _warehouse_to_tank,
    (Warehouse, Artillery):      _warehouse_to_artillery,
    (Warehouse, ReconOperator):  _warehouse_to_recon_op,
    (Warehouse, FPVOperator):    _warehouse_to_fpv_op,
    (Warehouse, SupplyTruck):    _warehouse_to_truck,
    (Warehouse, RadarEW):        _warehouse_to_radar_ew,
    (Warehouse, SoldierUnit):    _warehouse_to_soldier_unit,

    (SupplyCache, Infantry):     _warehouse_to_infantry,
    (SupplyCache, Tank):         _warehouse_to_tank,
    (SupplyCache, Artillery):    _warehouse_to_artillery,
    (SupplyCache, ReconOperator): _warehouse_to_recon_op,
    (SupplyCache, FPVOperator):  _warehouse_to_fpv_op,
    (SupplyCache, SupplyTruck):  _warehouse_to_truck,
    (SupplyCache, RadarEW):      _warehouse_to_radar_ew,
    (SupplyCache, SoldierUnit):  _warehouse_to_soldier_unit,

    (SupplyTruck, Infantry):     _truck_to_infantry,
    (SupplyTruck, Tank):         _truck_to_tank,
    (SupplyTruck, ReconOperator): _truck_to_recon_op,
    (SupplyTruck, FPVOperator):  _truck_to_fpv_op,
    (SupplyTruck, SoldierUnit):  _truck_to_soldier_unit,
    (SupplyTruck, SupplyTruck):  _truck_to_truck,
    (SupplyTruck, Artillery):    _truck_to_artillery,

    (Artillery, Infantry):       _artillery_to_infantry,
    (Artillery, Tank):           _artillery_to_tank,
    (Artillery, Artillery):      _artillery_to_artillery,

    (SoldierUnit, Infantry):     _soldier_unit_to_infantry,
    (SoldierUnit, SoldierUnit):  _soldier_unit_to_soldier_unit,

    (ReconOperator, ReconDrone): _recon_op_to_drone,
    (FPVOperator, FPVOperator):  _fpv_op_to_fpv_op,
}


def can_accept_resource(unit, res_type):
    """Check whether *unit* can receive more of *res_type*."""
    if isinstance(unit, Infantry):
        if res_type == "food":
            return any(s.food < s.max_food for s in unit.alive_soldiers)
        elif res_type == "ammo":
            return any(s.ammo < s.max_ammo for s in unit.alive_soldiers)
    elif isinstance(unit, Tank):
        if res_type == "ammo":
            return unit.ammo < unit.max_ammo
        elif res_type == "fuel":
            return unit.fuel < unit.max_fuel
        elif res_type == "food":
            return (unit.carry_food < unit.max_carry_food or
                    any(s.food < s.max_food for s in unit.alive_soldiers))
    elif isinstance(unit, Artillery):
        if res_type == "ammo":
            return unit.ammo < unit.max_ammo
        elif res_type == "food":
            return any(s.food < s.max_food for s in unit.alive_soldiers)
    elif isinstance(unit, ReconOperator):
        if res_type == "batteries":
            return unit.batteries < unit.max_batteries
        elif res_type == "food":
            return unit.food < unit.max_food
        elif res_type == "ammo":
            return unit.ammo < unit.max_ammo
    elif isinstance(unit, FPVOperator):
        if res_type == "fpv":
            return unit.fpv_stock < unit.max_stock
        elif res_type == "food":
            return unit.food < unit.max_food
        elif res_type == "ammo":
            return unit.ammo < unit.max_ammo
    elif isinstance(unit, ReconDrone):
        if res_type == "batteries":
            return unit.battery < unit.max_battery
    elif isinstance(unit, SoldierUnit):
        if res_type == "food":
            return unit.soldier.food < unit.soldier.max_food
        elif res_type == "ammo":
            return unit.soldier.ammo < unit.soldier.max_ammo
    elif isinstance(unit, RadarEW):
        if res_type == "fuel":
            return unit.fuel < unit.max_fuel
        elif res_type == "food":
            return unit.food < unit.max_food
        elif res_type == "ammo":
            return unit.ammo < unit.max_ammo
    elif isinstance(unit, (Warehouse, SupplyCache)):
        return True
    elif isinstance(unit, SupplyTruck):
        return unit.weight_remaining > 0
    return False


# ─── public API ───────────────────────────────────────────────────────

def transfer(source, target, res_type, limit=config.TRANSFER_DEFAULT_LIMIT):
    """Transfer *res_type* from *source* to *target* (up to *limit* units).

    Returns the amount actually transferred (0 if nothing moved).
    No validation is performed — callers must check alive / faction / distance
    beforehand.
    """
    key = (type(source), type(target))
    handler = _TRANSFER_TABLE.get(key)
    if handler is None:
        return 0
    return handler(source, target, res_type, limit)
