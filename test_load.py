from game.game import Game
from game import config

g = Game('ai')

# Find infantry and truck
inf = None
truck = None
for u in g.player_units:
    if u.type == 'infantry' and not inf:
        inf = u
    if u.type == 'supply_truck' and not truck:
        truck = u
    if inf and truck:
        break

if inf and truck:
    print(f"Infantry: {inf.name} at ({inf.x}, {inf.y})")
    print(f"  Soldiers: {inf.soldiers}, Food: {inf.food}/{inf.max_food}")
    print(f"Truck: {truck.name} at ({truck.x}, {truck.y})")
    print(f"  Crew: {truck.crew}/{truck.max_soldiers}")
    
    # Move them to same cell
    # Move truck to infantry position
    g.selected_unit = truck
    result = g.move_selected_unit(inf.x, inf.y)
    print(f"\nTruck moved to infantry: {result}")
    print(f"Truck new position: ({truck.x}, {truck.y})")
    
    # Now try to load infantry into truck
    print(f"\nLoading infantry into truck...")
    result = inf.load_into_truck(truck)
    print(f"Load result: {result}")
    print(f"Infantry loaded_in_truck: {inf.loaded_in_truck}")
    print(f"Infantry soldiers: {inf.soldiers}")
    print(f"Truck crew: {truck.crew}/{truck.max_soldiers}")
    print(f"Truck soldiers: {len(truck.alive_soldiers)}")
    
    # Now try to unload
    print(f"\nUnloading infantry...")
    result = inf.unload_from_truck(truck.x + 1, truck.y)
    print(f"Unload result: {result}")
    print(f"Infantry loaded_in_truck: {inf.loaded_in_truck}")
    print(f"Infantry soldiers: {inf.soldiers}")
    print(f"Infantry position: ({inf.x}, {inf.y})")