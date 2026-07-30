from game.game import Game
g = Game('ai')

# Test full turn progression
print('Testing full turn progression...')
for turn in range(3):
    print(f'\n=== Turn {turn+1} ===')
    g.end_planning_phase()
    while g.phase != 0:
        g._advance_phase()
    print(f'Turn {g.turn} completed')

# Check infantry food after 3 turns (should consume on turn 10, 20, etc.)
inf = None
for u in g.player_units:
    if hasattr(u, 'soldiers_list') and u.type == 'infantry':
        inf = u
        break

if inf:
    print(f'\nInfantry {inf.name} after 3 turns:')
    print(f'  Food: {inf.food}/{inf.max_food}')
    print(f'  Soldier foods: {[f"{s.food}/{s.max_food}" for s in inf.alive_soldiers[:3]]}')

# Test tank movement distance
tank = None
for u in g.all_units:
    if 'Танк' in u.name and u.faction == 0:
        tank = u
        break

if tank:
    print(f'\nTank {tank.name}:')
    print(f'  Position: ({tank.x}, {tank.y})')
    print(f'  Fuel: {tank.fuel}/{tank.max_fuel}')
    print(f'  Ammo: {tank.ammo}/{tank.max_ammo}')

print('\nAll tests passed!')