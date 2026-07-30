from game.game import Game
g = Game('ai')

# Check infantry food consumption
inf = None
for u in g.player_units:
    if hasattr(u, 'soldiers_list') and u.type == 'infantry':
        inf = u
        break

if inf:
    print(f'Infantry: {inf.name}')
    print(f'  Soldiers: {inf.soldiers}')
    print(f'  Food: {inf.food}/{inf.max_food}')
    print(f'  Ammo: {inf.ammo}/{inf.max_ammo}')
    print(f'  Soldiers food: {[f"{s.food}/{s.max_food}" for s in inf.alive_soldiers[:3]]}')
    print(f'  Soldiers ammo: {[f"{s.ammo}/{s.max_ammo}" for s in inf.alive_soldiers[:3]]}')

# Check soldier unit
su = None
for u in g.all_units:
    if hasattr(u, 'soldier') and u.type == 'soldier_unit':
        su = u
        break
if su:
    print(f'\nSoldierUnit: {su.name}')
    print(f'  Food: {su.food}/{su.max_food}')
    print(f'  Ammo: {su.ammo}/{su.max_ammo}')
    print(f'  Soldier food: {su.soldier.food}/{su.soldier.max_food}')

# Check FPVOperator
for u in g.player_units:
    if u.type == 'fpv_operator':
        print(f'\nFPVOperator: {u.name}')
        print(f'  Food: {u.food}/{u.max_food}')
        print(f'  Ammo: {u.ammo}/{u.max_ammo}')
        break

# Check ReconOperator
for u in g.player_units:
    if u.type == 'recon_operator':
        print(f'\nReconOperator: {u.name}')
        print(f'  Food: {u.food}/{u.max_food}')
        print(f'  Ammo: {u.ammo}/{u.max_ammo}')
        break

# Check Tank
for u in g.player_units:
    if u.type == 'tank':
        print(f'\nTank: {u.name}')
        print(f'  Fuel: {u.fuel}/{u.max_fuel}')
        print(f'  Ammo: {u.ammo}/{u.max_ammo}')
        break

# Test food consumption
print('\n--- Testing food consumption (turn 10) ---')
g.turn = 10
inf.consume_food(10)
print(f'Infantry food after consume: {inf.food}')
print(f'Soldier food: {[s.food for s in inf.alive_soldiers[:3]]}')

# Test soldier unit food consumption
su.consume_food()
print(f'SoldierUnit food after consume: {su.food}')
print(f'Soldier food: {su.soldier.food}')

# Test FOOD_CONSUMPTION_INTERVAL
from game import config
print(f'\nFOOD_CONSUMPTION_INTERVAL: {config.FOOD_CONSUMPTION_INTERVAL}')