"""Система сохранения и загрузки игры"""
import os
import pickle
from datetime import datetime


class SaveLoadSystem:
    """Система сохранения и загрузки состояния игры"""
    
    SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'saves')
    
    @classmethod
    def ensure_save_dir(cls):
        """Создать директорию для сохранений если её нет"""
        if not os.path.exists(cls.SAVE_DIR):
            os.makedirs(cls.SAVE_DIR)
    
    @classmethod
    def save_game(cls, game, slot_name="autosave"):
        """Сохранить игру"""
        cls.ensure_save_dir()
        
        save_data = {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'turn': game.turn,
            'phase': game.phase,
            'game_state': cls._serialize_game(game),
        }
        
        filepath = os.path.join(cls.SAVE_DIR, f"{slot_name}.sav")
        with open(filepath, 'wb') as f:
            pickle.dump(save_data, f)
        
        return filepath
    
    @classmethod
    def load_game(cls, slot_name="autosave"):
        """Загрузить игру"""
        cls.ensure_save_dir()
        
        filepath = os.path.join(cls.SAVE_DIR, f"{slot_name}.sav")
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'rb') as f:
            save_data = pickle.load(f)
        
        return save_data
    
    @classmethod
    def list_saves(cls):
        """Получить список сохранений"""
        cls.ensure_save_dir()
        
        saves = []
        for filename in os.listdir(cls.SAVE_DIR):
            if filename.endswith('.sav'):
                filepath = os.path.join(cls.SAVE_DIR, filename)
                try:
                    with open(filepath, 'rb') as f:
                        data = pickle.load(f)
                    saves.append({
                        'name': filename[:-4],
                        'timestamp': data.get('timestamp', 'unknown'),
                        'turn': data.get('turn', 0),
                    })
                except:
                    pass
        
        return sorted(saves, key=lambda x: x['timestamp'], reverse=True)
    
    @classmethod
    def delete_save(cls, slot_name):
        """Удалить сохранение"""
        filepath = os.path.join(cls.SAVE_DIR, f"{slot_name}.sav")
        if os.path.exists(filepath):
            os.remove(filepath)
    
    @classmethod
    def _serialize_game(cls, game):
        """Сериализовать состояние игры"""
        # Используем pickle для простоты
        # В будущем можно использовать JSON для лучшей совместимости
        return {
            'turn': game.turn,
            'phase': game.phase,
            'map_data': game.map.serialize() if hasattr(game.map, 'serialize') else None,
            'units': [cls._serialize_unit(u) for u in game.all_units],
            'player_units_count': len(game.player_units),
            'enemy_units_count': len(game.enemy_units),
        }
    
    @classmethod
    def _serialize_unit(cls, unit):
        """Сериализовать юнит"""
        return {
            'type': unit.__class__.__name__,
            'x': unit.x,
            'y': unit.y,
            'faction': unit.faction,
            'name': unit.name,
            'alive': unit.is_alive,
            'data': {k: v for k, v in unit.__dict__.items() 
                    if not k.startswith('_') and not callable(v)}
        }
    
    @classmethod
    def restore_game(cls, game, save_data):
        """Восстановить состояние игры из сохранённых данных"""
        if not save_data:
            return False
        
        game_state = save_data.get('game_state', {})
        game.turn = game_state.get('turn', 0)
        game.phase = game_state.get('phase', 0)
        
        # Очистить текущие юниты
        game.all_units.clear()
        game.player_units.clear()
        game.enemy_units.clear()
        
        # Восстановить юниты
        from ..units import Infantry, Tank, ReconDrone, SupplyTruck, Warehouse, FPVOperator, FPVDrone, ReconOperator, SupplyCache, RadarEW
        
        unit_classes = {
            'Infantry': Infantry,
            'Tank': Tank,
            'ReconDrone': ReconDrone,
            'SupplyTruck': SupplyTruck,
            'Warehouse': Warehouse,
            'FPVOperator': FPVOperator,
            'FPVDrone': FPVDrone,
            'ReconOperator': ReconOperator,
            'SupplyCache': SupplyCache,
            'RadarEW': RadarEW,
        }
        
        for unit_data in game_state.get('units', []):
            unit_type = unit_data.get('type')
            if unit_type not in unit_classes:
                continue
            
            unit_class = unit_classes[unit_type]
            data = unit_data.get('data', {})
            
            # Создать юнит
            unit = unit_class(
                data.get('x', 0),
                data.get('y', 0),
                data.get('faction', 0),
                data.get('name', unit_type)
            )
            
            # Восстановить атрибуты
            for key, value in data.items():
                if hasattr(unit, key):
                    setattr(unit, key, value)
            
            game.all_units.append(unit)
            if unit.faction == 0:  # PLAYER
                game.player_units.append(unit)
            else:
                game.enemy_units.append(unit)
            
            game.map.add_unit(unit, unit.x, unit.y)
        
        return True
