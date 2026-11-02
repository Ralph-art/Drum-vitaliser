"""
Reaper Integration Module

Integreert met Reaper via ReaScript (Python).
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ReaperIntegration:
    """
    Integreert de MIDI Drum Generator met Reaper.
    """

    def __init__(self):
        self.reaper_executable: Optional[str] = None
        self._find_reaper()

    def _find_reaper(self) -> bool:
        """Vind de Reaper executable."""
        # Standaard locaties op Linux
        possible_locations = [
            "/usr/bin/reaper",
            "/usr/local/bin/reaper",
            "/opt/reaper/reaper",
            os.path.expanduser("~/reaper/reaper"),
            os.path.expanduser("~/bin/reaper"),
        ]

        for loc in possible_locations:
            if os.path.exists(loc) and os.access(loc, os.X_OK):
                self.reaper_executable = loc
                logger.info(f"Reaper gevonden: {loc}")
                return True

        # Probeer via which
        try:
            result = subprocess.run(
                ["which", "reaper"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.reaper_executable = result.stdout.strip()
                logger.info(f"Reaper gevonden via which: {self.reaper_executable}")
                return True
        except Exception as e:
            logger.warning(f"Kon Reaper niet vinden via which: {e}")

        logger.warning("Reaper executable niet gevonden. Zorg dat Reaper geinstalleerd is.")
        return False

    def is_reaper_available(self) -> bool:
        """Check of Reaper beschikbaar is."""
        return self.reaper_executable is not None

    def _run_reaper_script(self, script_content: str, script_name: str = "midi_drum_gen") -> bool:
        """Voer een ReaScript uit."""
        if not self.is_reaper_available():
            logger.error("Reaper is niet beschikbaar")
            return False

        # Maak een tijdelijke directory voor het script
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, f"{script_name}.py")

            # Schrijf het script
            with open(script_path, 'w') as f:
                f.write(script_content)

            # Voer uit via Reaper
            try:
                cmd = [
                    self.reaper_executable,
                    "-script", script_path
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode != 0:
                    logger.error(f"ReaScript mislukt: {result.stderr}")
                    return False

                logger.info(f"ReaScript uitgevoerd: {result.stdout}")
                return True

            except subprocess.TimeoutExpired:
                logger.error("ReaScript timeout")
                return False
            except Exception as e:
                logger.error(f"Fout bij uitvoeren ReaScript: {e}")
                return False

    def _create_reascript(self, midi_file_path: str, output_track_name: str = "Drum Generator") -> str:
        """Maak een ReaScript om MIDI te importeren."""
        script = f"""
import reaper
import os

# Laad MIDI-bestand
midi_path = r\"{midi_file_path}\"

# Check of bestand bestaat
if not os.path.exists(midi_path):
    reaper.ShowMessageBox(\"MIDI-bestand niet gevonden: \" + midi_path, \"Fout\", 0)
    exit()

# Voeg een nieuwe track toe
reaper.InsertTrackAtIndex(reaper.CountTracks(0), True)
new_track = reaper.GetTrack(0, reaper.CountTracks(0) - 1)

# Naam van de track
reaper.GetSetMediaTrackInfo_String(new_track, \"P_NAME\", \"{output_track_name}\", True)

# Laad MIDI-bestand in de track
reaper.GetSetMediaTrackInfo_String(new_track, \"P_SOURCE\", midi_path, True)

# Zorg dat de track MIDI is
reaper.SetMediaTrackInfo_Value(new_track, \"I_FXEN\", 0)
reaper.SetTrackState(new_track, 0)

# Selecteer de nieuwe track
reaper.SetOnlyTrackSelected(new_track)

# Zoom naar de nieuwe track
reaper.Main_OnCommand(40446, 0)  # Scroll to selected track

reaper.UpdateArrange()
reaper.ShowMessageBox(\"MIDI drum pattern geimporteerd!\", \"Succes\", 0)
"""
        return script

    def import_midi_to_reaper(self, midi_file_path: str,
                             output_track_name: str = "Drum Generator") -> bool:
        """Importeer een MIDI-bestand in Reaper."""
        if not os.path.exists(midi_file_path):
            logger.error(f"MIDI-bestand niet gevonden: {midi_file_path}")
            return False

        script = self._create_reascript(midi_file_path, output_track_name)
        return self._run_reaper_script(script)

    def get_reaper_scripts_directory(self) -> Optional[str]:
        """Krijg de Reaper Scripts directory."""
        # Standaard locaties op Linux
        possible_dirs = [
            os.path.expanduser("~/.config/REAPER/Scripts/"),
            os.path.expanduser("~/reaper/scripts/"),
        ]

        for dir_path in possible_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                return dir_path

        return None

    def create_reascript_file(self, script_path: str) -> bool:
        """Maak een permanent ReaScript bestand."""
        script_content = """
# MIDI Drum Generator ReaScript
# Plaats dit bestand in de Reaper Scripts directory
# (meestal: ~/.config/REAPER/Scripts/)

import reaper
import os
import sys

# Voeg de project directory toe
# Pas dit aan naar de locatie van je midi_drum_generator directory
PROJECT_DIR = \"/path/to/midi_drum_generator\"
sys.path.insert(0, PROJECT_DIR)

from midi_drum_generator.midi_analyzer import MIDIAnalyzer
from midi_drum_generator.drum_generator import DrumGenerator, GenerationConfig

def show_gui():
    # Vraag om bron MIDI-bestand
    result, midi_path = reaper.GetUserFileNameForRead(
        \"Selecteer bron MIDI-bestand\",\n        \"MIDI Files (*.mid *.midi)\\\\0*.mid;*.midi\\\\0All Files (*.*)\\\\0*.*\\\\0\"\n    )

    if not result:
        return

    # Vraag om aantal maten
    result, num_measures_str = reaper.GetUserInputs(
        \"MIDI Drum Generator\",\n        1,\n        \"Aantal maten:,extrawidth=200\"\n    )

    if not result:
        return

    try:
        num_measures = int(num_measures_str)
    except:
        num_measures = 8

    # Genereer en importeer
    try:
        analyzer = MIDIAnalyzer()
        patterns = analyzer.extract_patterns(midi_path)

        if not patterns:
            reaper.ShowMessageBox(\"Geen drum patterns gevonden\", \"Fout\", 0)
            return

        pattern = patterns[0]

        config = GenerationConfig(
            variation=0.3,
            complexity=0.5
        )

        generator = DrumGenerator(config)
        new_pattern = generator.generate_from_pattern(pattern, num_measures=num_measures)

        # Exporteer naar tijdelijk bestand
        temp_dir = reaper.GetResourcePath() + \"/Data/temp_midi_drum_gen\"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        output_path = temp_dir + \"/generated_drums.mid\"
        generator.export_to_midi(new_pattern, output_path)

        # Importeer in Reaper
        reaper.InsertTrackAtIndex(reaper.CountTracks(0), True)
        new_track = reaper.GetTrack(0, reaper.CountTracks(0) - 1)
        reaper.GetSetMediaTrackInfo_String(new_track, \"P_NAME\", \"Generated Drums\", True)
        reaper.GetSetMediaTrackInfo_String(new_track, \"P_SOURCE\", output_path, True)

        reaper.SetOnlyTrackSelected(new_track)
        reaper.Main_OnCommand(40446, 0)
        reaper.UpdateArrange()

        reaper.ShowMessageBox(\"Drum pattern gegenereerd!\", \"Succes\", 0)

    except Exception as e:
        reaper.ShowMessageBox(\"Fout: \" + str(e), \"Fout\", 0)

# Voer uit
if __name__ == \"__main__\":\n    show_gui()
"""

        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            logger.info(f"ReaScript gemaakt: {script_path}")
            return True
        except Exception as e:
            logger.error(f"Kon ReaScript niet maken: {e}")
            return False

    def install_reascript(self) -> bool:
        """Installeer het ReaScript in de Reaper Scripts directory."""
        scripts_dir = self.get_reaper_scripts_directory()

        if scripts_dir is None:
            # Maak directory aan
            scripts_dir = os.path.expanduser("~/.config/REAPER/Scripts/")
            try:
                os.makedirs(scripts_dir, exist_ok=True)
            except Exception as e:
                logger.error(f"Kon Scripts directory niet maken: {e}")
                return False

        script_path = os.path.join(scripts_dir, "midi_drum_generator.py")
        return self.create_reascript_file(script_path)

    def generate_and_import(self, source_midi_path: str,
                           num_measures: int = 8) -> bool:
        """Genereer een drum pattern en importeer in Reaper."""
        if not os.path.exists(source_midi_path):
            logger.error(f"Bron MIDI-bestand niet gevonden: {source_midi_path}")
            return False

        # Maak een tijdelijk MIDI-bestand
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as temp_midi:
            output_midi_path = temp_midi.name

        try:
            # Analyseer en genereer
            from .midi_analyzer import MIDIAnalyzer
            from .drum_generator import DrumGenerator, GenerationConfig

            analyzer = MIDIAnalyzer()
            patterns = analyzer.extract_patterns(source_midi_path)

            if not patterns:
                logger.error("Geen drum patterns gevonden in bronbestand")
                return False

            pattern = patterns[0]

            config = GenerationConfig(
                variation=0.3,
                complexity=0.5,
                seed=None
            )

            generator = DrumGenerator(config)
            new_pattern = generator.generate_from_pattern(pattern, num_measures=num_measures)

            # Exporteer
            generator.export_to_midi(new_pattern, output_midi_path)

            # Importeer in Reaper
            return self.import_midi_to_reaper(output_midi_path, "Generated Drums")

        finally:
            # Verwijder tijdelijk bestand
            if os.path.exists(output_midi_path):
                os.unlink(output_midi_path)

    def create_midi_from_template(self, template_path: str,
                                  output_path: str,
                                  config: Optional[Dict] = None) -> bool:
        """Maak een MIDI-bestand van een template."""
        try:
            from .midi_analyzer import MIDIAnalyzer
            from .drum_generator import DrumGenerator, GenerationConfig

            # Analyseer template
            analyzer = MIDIAnalyzer()
            patterns = analyzer.extract_patterns(template_path)

            if not patterns:
                logger.error("Geen drum patterns gevonden in template")
                return False

            pattern = patterns[0]

            # Genereer nieuw pattern
            gen_config = GenerationConfig(**config) if config else GenerationConfig()
            generator = DrumGenerator(gen_config)
            new_pattern = generator.generate_from_pattern(pattern)

            # Exporteer
            generator.export_to_midi(new_pattern, output_path)
            logger.info(f"MIDI-bestand gemaakt: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Fout bij maken MIDI: {e}")
            return False
