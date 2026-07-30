"""Загрузчик конфигурации юнитов из JSON файлов"""
import json
import os


class UnitConfigLoader:
    """Загружает конфигурацию юнитов из JSON файлов"""
    
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), 'unit_configs')
        self.config_dir = config_dir
        self._cache = {}
    
    def load_unit_config(self, unit_type):
        """Загрузить конфигурацию для типа юнита"""
        if unit_type in self._cache:
            return self._cache[unit_type]
        
        config_file = os.path.join(self.config_dir, 'units.json')
        if not os.path.exists(config_file):
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            all_configs = json.load(f)
        
        self._cache = all_configs
        return all_configs.get(unit_type, {})
    
    def get_all_configs(self):
        """Получить все конфигурации"""
        if not self._cache:
            config_file = os.path.join(self.config_dir, 'units.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
        return self._cache
    
    def reload(self):
        """Перезагрузить конфигурации"""
        self._cache = {}
        return self.get_all_configs()


# Глобальный загрузчик
unit_config_loader = UnitConfigLoader()
