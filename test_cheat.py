import sys
sys.path.insert(0, '.')
from game import Game
from game import config

g = Game(game_mode='ai')
print('Checking map structure...')
print(f'Map type: {type(g.map)}')
print(f'Map has cells: {hasattr(g.map, "cells")}')
print(f'Map has get_cell: {hasattr(g.map, "get_cell")}')

if hasattr(g.map, 'cells'):
    print(f'Cells type: {type(g.map.cells)}')
    print(f'Cells length: {len(g.map.cells)}')
    if len(g.map.cells) > 0:
        print(f'First cell type: {type(g.map.cells[0])}')
        print(f'First cell has visible: {hasattr(g.map.cells[0], "visible")}')
