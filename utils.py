"""
Utility functions voor MIDI Drum Generator.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

def setup_logging(level: int = logging.INFO) -> None:
    """Configureer logging."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('midi_drum_generator.log')
        ]
    )

def get_example_midi_files(directory: str = "examples") -> List[str]:
    """Krijg lijst van voorbeeld MIDI-bestanden."""
    midi_files = []

    if not os.path.exists(directory):
        return midi_files

    for file in os.listdir(directory):
        if file.lower().endswith(('.mid', '.midi')):
            midi_files.append(os.path.join(directory, file))

    return midi_files

def create_example_midi() -> Optional[str]:
    """Maak een voorbeeld MIDI-bestand voor testen."""
    import mido
    from mido import MidiFile, MidiTrack, Message, MetaMessage

    try:
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)

        # Set tempo to 120 BPM (500000 microseconds per beat)
        track.append(MetaMessage('set_tempo', tempo=500000, time=0))

        # Set time signature to 4/4
        track.append(MetaMessage('time_signature', numerator=4, denominator=4, time=0))

        # Kick on beats 1 and 3
        track.append(Message('note_on', note=36, velocity=100, time=0, channel=9))
        track.append(Message('note_off', note=36, velocity=0, time=480, channel=9))

        track.append(Message('note_on', note=36, velocity=100, time=480, channel=9))
        track.append(Message('note_off', note=36, velocity=0, time=480, channel=9))

        # Snare on beats 2 and 4
        track.append(Message('note_on', note=38, velocity=90, time=480, channel=9))
        track.append(Message('note_off', note=38, velocity=0, time=480, channel=9))

        track.append(Message('note_on', note=38, velocity=90, time=480, channel=9))
        track.append(Message('note_off', note=38, velocity=0, time=480, channel=9))

        # Hi-hat on every 8th note
        for i in range(8):
            track.append(Message('note_on', note=42, velocity=70, time=240, channel=9))
            track.append(Message('note_off', note=42, velocity=0, time=0, channel=9))

        # Save
        output_path = "examples/basic_drum_pattern.mid"
        os.makedirs("examples", exist_ok=True)
        mid.save(output_path)

        logger.info(f"Voorbeeld MIDI-bestand gemaakt: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Kon voorbeeld MIDI niet maken: {e}")
        return None

def validate_midi_file(filepath: str) -> bool:
    """Valideer een MIDI-bestand."""
    import mido

    try:
        mid = mido.MidiFile(filepath)

        # Check if it has tracks
        if not mid.tracks:
            logger.warning(f"MIDI-bestand heeft geen tracks: {filepath}")
            return False

        # Check for drum notes
        has_drum_notes = False
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'note_on' and 35 <= msg.note <= 81:
                    has_drum_notes = True
                    break
            if has_drum_notes:
                break

        if not has_drum_notes:
            logger.warning(f"Geen drum notes gevonden in: {filepath}")
            return False

        logger.info(f"MIDI-bestand valide: {filepath}")
        return True

    except Exception as e:
        logger.error(f"Ongeldig MIDI-bestand: {filepath} - {e}")
        return False

def get_project_root() -> Path:
    """Krijg de root directory van het project."""
    return Path(__file__).parent.parent
