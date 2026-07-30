"""Конфигурация"""
# Import all constants from the main game config file
from ..game_config import *
from .config_loader import unit_config_loader, UnitConfigLoader

__all__ = ['unit_config_loader', 'UnitConfigLoader']
