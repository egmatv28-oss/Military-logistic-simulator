from game.game import Game
from game import config

g = Game('ai')

# Find truck
truck = None
for u in g.player_units:
    if u.type == 'supply_truck':
        truck = u
        break

if truck:
    print(f"Initial truck position: ({truck.x}, {truck.y})")
    print(f"Truck fuel: {truck.fuel}/{truck.max_fuel}")
    
    # Move truck manually to test movement
    g.selected_unit = truck
    
    # Try to move 3 cells away
    target_x = truck.x + 3
    target_y = truck.y
    
    cell = g.map.get_cell(target_x, target_y)
    if cell and cell.is_walkable:
        print(f"Target ({target_x}, {target_y}) is walkable")
        dist = abs(truck.x - target_x) + abs(truck.y - target_y)
        print(f"Distance: {dist}")
        
        result = g.move_selected_unit(target_x, target_y)
        print(f"Move result: {result}")
        print(f"New truck position: ({truck.x}, {truck.y})")
        print(f"Truck fuel after move: {truck.fuel}/{truck.max_fuel}")
    else:
        print(f"Target ({target_x}, {target_y}) not walkable")