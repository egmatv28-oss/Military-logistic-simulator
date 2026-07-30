from game.game import Game
from game import config

g = Game('ai')

# Find tank
tank = None
for u in g.player_units:
    if u.type == 'tank':
        tank = u
        break

if tank:
    print(f"Initial tank position: ({tank.x}, {tank.y})")
    print(f"Tank fuel: {tank.fuel}/{tank.max_fuel}")
    
    # Move tank manually to test movement
    # In planning phase, we can give orders
    g.selected_unit = tank
    
    # Try to move 3 cells away
    target_x = tank.x + 3
    target_y = tank.y
    
    # Check if it's valid
    cell = g.map.get_cell(target_x, target_y)
    if cell and cell.is_walkable:
        print(f"Target ({target_x}, {target_y}) is walkable")
        # Check distance
        dist = abs(tank.x - target_x) + abs(tank.y - target_y)
        print(f"Distance: {dist}")
        
        # Try moving
        result = g.move_selected_unit(target_x, target_y)
        print(f"Move result: {result}")
        print(f"New tank position: ({tank.x}, {tank.y})")
        print(f"Tank fuel after move: {tank.fuel}/{tank.max_fuel}")
    else:
        print(f"Target ({target_x}, {target_y}) not walkable")