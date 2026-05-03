"""SCOUT — Startup Intelligence Module for GIGSAW."""

__version__ = '0.1.0'

from scout.config import Config
from scout.feed import Feed
from scout.storage import ScoutStorage

__all__ = ['Config', 'Feed', 'ScoutStorage']
