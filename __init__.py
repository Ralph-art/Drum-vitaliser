"""
MIDI Drum Generator for Reaper

Een tool om drum patterns te genereren gebaseerd op bestaande MIDI-bestanden.
Werkt binnen Reaper via ReaScript (Python).
"""

__version__ = "1.0.0"
__author__ = "Ralph-art"

from .midi_analyzer import MIDIAnalyzer
from .drum_generator import DrumGenerator
from .reaper_integration import ReaperIntegration

__all__ = ["MIDIAnalyzer", "DrumGenerator", "ReaperIntegration"]
