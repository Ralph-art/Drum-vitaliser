"""
MIDI Analyzer Module

Analyseert MIDI-bestanden om drum patterns, tempo en structuur te extraheren.
"""

import mido
from mido import MidiFile, MidiTrack, Message
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Standaard drum note mappings (General MIDI)
DRUM_NOTE_NAMES = {
    35: "Acoustic Bass Drum",
    36: "Bass Drum 1",
    37: "Side Stick",
    38: "Acoustic Snare",
    39: "Hand Clap",
    40: "Electric Snare",
    41: "Low Floor Tom",
    42: "Closed Hi-Hat",
    43: "High Floor Tom",
    44: "Pedal Hi-Hat",
    45: "Low Tom",
    46: "Open Hi-Hat",
    47: "Low-Mid Tom",
    48: "Hi-Mid Tom",
    49: "Crash Cymbal 1",
    50: "High Tom",
    51: "Ride Cymbal 1",
    52: "Chinese Cymbal",
    53: "Ride Cymbal 2",
    54: "Tambourine",
    55: "Splash Cymbal",
    56: "Cowbell",
    57: "Crash Cymbal 2",
    58: "Vibraslap",
    59: "Ride Cymbal 3",
    60: "Hi Bongo",
    61: "Low Bongo",
    62: "Mute Hi Conga",
    63: "Open Hi Conga",
    64: "Low Conga",
    65: "High Timbale",
    66: "Low Timbale",
    67: "High Agogo",
    68: "Low Agogo",
    69: "Cabasa",
    70: "Maracas",
    71: "Short Whistle",
    72: "Long Whistle",
    73: "Short Guiro",
    74: "Long Guiro",
    75: "Claves",
    76: "Hi Wood Block",
    77: "Low Wood Block",
    78: "Mute Cuica",
    79: "Open Cuica",
    80: "Mute Triangle",
    81: "Open Triangle",
}

# Categorien voor drum notes
DRUM_CATEGORIES = {
    "kick": [35, 36],
    "snare": [38, 40],
    "tom": [41, 43, 45, 47, 48, 50],
    "hi_hat": [42, 44, 46],
    "cymbal": [49, 51, 52, 53, 57, 59],
    "percussion": [37, 39, 54, 55, 56, 58, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81],
}

@dataclass
class DrumHit:
    """Represents a single drum hit."""
    note: int
    velocity: int
    time: float  # in seconds
    category: str
    name: str

@dataclass
class Measure:
    """Represents a musical measure."""
    start_time: float
    end_time: float
    tempo: float
    hits: List[DrumHit] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

@dataclass
class Pattern:
    """Represents a drum pattern."""
    name: str
    measures: List[Measure] = field(default_factory=list)
    tempo: float = 120.0
    time_signature: Tuple[int, int] = (4, 4)

    @property
    def total_duration(self) -> float:
        if not self.measures:
            return 0.0
        return self.measures[-1].end_time

class MIDIAnalyzer:
    """
    Analyseert MIDI-bestanden om drum patterns te extraheren.
    """

    def __init__(self):
        self.ticks_per_beat: Optional[int] = None
        self.tempo: float = 120.0
        self.time_signature: Tuple[int, int] = (4, 4)

    def load_midi(self, filepath: str) -> MidiFile:
        """Laad een MIDI-bestand."""
        try:
            mid = MidiFile(filepath)
            self.ticks_per_beat = mid.ticks_per_beat
            logger.info(f"Geladen: {filepath} ({self.ticks_per_beat} ticks per beat)")
            return mid
        except Exception as e:
            logger.error(f"Fout bij laden van {filepath}: {e}")
            raise

    def _get_note_category(self, note: int) -> str:
        """Bepaal de categorie van een drum note."""
        for category, notes in DRUM_CATEGORIES.items():
            if note in notes:
                return category
        return "unknown"

    def _get_note_name(self, note: int) -> str:
        """Krijg de naam van een drum note."""
        return DRUM_NOTE_NAMES.get(note, f"Unknown ({note})")

    def _ticks_to_seconds(self, ticks: int, tempo: float, ticks_per_beat: int) -> float:
        """Converteer ticks naar seconden."""
        if ticks_per_beat <= 0:
            return 0.0
        beats = ticks / ticks_per_beat
        return beats * (60.0 / tempo)

    def extract_drum_track(self, mid: MidiFile) -> Optional[MidiTrack]:
        """Vind en retourneer de drum track in een MIDI-bestand."""
        # Zoek naar tracks met drum channel (meestal channel 10)
        for i, track in enumerate(mid.tracks):
            drum_messages = []
            for msg in track:
                if msg.type == 'note_on' and msg.channel == 9:  # Channel 10 is index 9
                    drum_messages.append(msg)

            # Als er genoeg drum notes zijn, is dit waarschijnlijk de drum track
            if len(drum_messages) > 10:
                logger.info(f"Drum track gevonden: track {i} ({len(drum_messages)} drum notes)")
                return track

        # Zoek naar tracks met drum notes op welk channel dan ook
        for i, track in enumerate(mid.tracks):
            drum_messages = []
            for msg in track:
                if msg.type == 'note_on' and msg.note in DRUM_NOTE_NAMES:
                    drum_messages.append(msg)

            if len(drum_messages) > 10:
                logger.info(f"Drum track gevonden op channel {msg.channel}: track {i} ({len(drum_messages)} drum notes)")
                return track

        # Return de eerste track als fallback
        if mid.tracks:
            logger.warning("Geen duidelijke drum track gevonden, gebruik eerste track")
            return mid.tracks[0]

        return None

    def extract_tempo(self, mid: MidiFile) -> float:
        """Extracteer tempo uit MIDI-bestand."""
        default_tempo = 120.0

        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    # Tempo is in microseconds per beat
                    microseconds_per_beat = msg.tempo
                    bpm = 60000000.0 / microseconds_per_beat
                    self.tempo = bpm
                    logger.info(f"Tempo gevonden: {bpm:.2f} BPM")
                    return bpm

        logger.warning(f"Geen tempo gevonden, gebruik default: {default_tempo} BPM")
        return default_tempo

    def extract_time_signature(self, mid: MidiFile) -> Tuple[int, int]:
        """Extracteer maatsoort uit MIDI-bestand."""
        default_ts = (4, 4)

        for track in mid.tracks:
            for msg in track:
                if msg.type == 'time_signature':
                    self.time_signature = (msg.numerator, msg.denominator)
                    logger.info(f"Tijdsignatuur gevonden: {msg.numerator}/{msg.denominator}")
                    return (msg.numerator, msg.denominator)

        logger.warning(f"Geen tijdsignatuur gevonden, gebruik default: {default_ts}")
        return default_ts

    def extract_drum_hits(self, track: MidiTrack, tempo: float, ticks_per_beat: int) -> List[DrumHit]:
        """Extracteer alle drum hits uit een track."""
        hits = []
        absolute_time = 0.0  # in seconds

        for msg in track:
            absolute_time += self._ticks_to_seconds(msg.time, tempo, ticks_per_beat)

            if msg.type == 'note_on' and msg.velocity > 0:
                # Alleen drum notes (35-81)
                if 35 <= msg.note <= 81:
                    category = self._get_note_category(msg.note)
                    name = self._get_note_name(msg.note)

                    hit = DrumHit(
                        note=msg.note,
                        velocity=msg.velocity,
                        time=absolute_time,
                        category=category,
                        name=name
                    )
                    hits.append(hit)

        logger.info(f"Extracteerde {len(hits)} drum hits")
        return hits

    def segment_into_measures(self, hits: List[DrumHit], tempo: float,
                              time_signature: Tuple[int, int]) -> List[Measure]:
        """Segment hits into measures based on time signature and tempo."""
        numerator, denominator = time_signature
        beats_per_measure = numerator
        beat_duration = 60.0 / tempo  # seconds per beat
        measure_duration = beats_per_measure * beat_duration

        measures = []
        if not hits:
            return measures

        # Start from the first hit
        current_measure_start = 0.0
        current_measure_end = measure_duration
        current_measure_hits = []

        for hit in hits:
            # If hit is beyond current measure, finalize current measure
            while hit.time >= current_measure_end:
                if current_measure_hits:
                    measure = Measure(
                        start_time=current_measure_start,
                        end_time=current_measure_end,
                        tempo=tempo,
                        hits=current_measure_hits
                    )
                    measures.append(measure)

                current_measure_start = current_measure_end
                current_measure_end += measure_duration
                current_measure_hits = []

            current_measure_hits.append(hit)

        # Add the last measure
        if current_measure_hits:
            measure = Measure(
                start_time=current_measure_start,
                end_time=current_measure_end,
                tempo=tempo,
                hits=current_measure_hits
            )
            measures.append(measure)

        logger.info(f"Gesegmenteerd in {len(measures)} maten")
        return measures

    def analyze_pattern(self, hits: List[DrumHit], measures: List[Measure]) -> Dict:
        """Analyseer het drum pattern."""
        if not hits:
            return {"error": "No hits to analyze"}

        # Count hits per category
        category_counts = {}
        for hit in hits:
            category_counts[hit.category] = category_counts.get(hit.category, 0) + 1

        # Count hits per measure
        hits_per_measure = [len(m.hits) for m in measures]

        # Calculate density
        total_hits = len(hits)
        total_measures = len(measures)
        density = total_hits / total_measures if total_measures > 0 else 0

        # Find most common pattern
        patterns = {}
        for measure in measures:
            # Create a simple pattern representation
            pattern_key = tuple(sorted([(h.category, int(h.time * 100) % 1000) for h in measure.hits]))
            patterns[pattern_key] = patterns.get(pattern_key, 0) + 1

        most_common_pattern = max(patterns.items(), key=lambda x: x[1]) if patterns else None

        return {
            "total_hits": total_hits,
            "total_measures": total_measures,
            "density": density,
            "category_counts": category_counts,
            "hits_per_measure": hits_per_measure,
            "most_common_pattern": most_common_pattern,
            "tempo": self.tempo,
            "time_signature": self.time_signature,
        }

    def extract_patterns(self, filepath: str) -> List[Pattern]:
        """Extracteer drum patterns uit een MIDI-bestand."""
        mid = self.load_midi(filepath)

        # Extract metadata
        tempo = self.extract_tempo(mid)
        time_signature = self.extract_time_signature(mid)
        ticks_per_beat = mid.ticks_per_beat

        # Extract drum track
        drum_track = self.extract_drum_track(mid)
        if drum_track is None:
            raise ValueError("Geen drum track gevonden in MIDI-bestand")

        # Extract hits
        hits = self.extract_drum_hits(drum_track, tempo, ticks_per_beat)

        # Segment into measures
        measures = self.segment_into_measures(hits, tempo, time_signature)

        # Create pattern
        pattern = Pattern(
            name=f"Pattern from {filepath}",
            measures=measures,
            tempo=tempo,
            time_signature=time_signature
        )

        return [pattern]

    def find_similar_measures(self, measures: List[Measure], threshold: float = 0.8) -> List[List[int]]:
        """Vind vergelijkbare maten."""
        similar_groups = []

        # Create similarity matrix
        n = len(measures)
        similarity = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    similarity[i][j] = 1.0
                    continue

                # Simple similarity based on hit categories at similar times
                hits_i = [(h.category, h.time) for h in measures[i].hits]
                hits_j = [(h.category, h.time) for h in measures[j].hits]

                # Count matching categories at similar positions
                matches = 0
                total = max(len(hits_i), len(hits_j))

                for hit_i in hits_i:
                    for hit_j in hits_j:
                        if hit_i[0] == hit_j[0] and abs(hit_i[1] - hit_j[1]) < 0.1:
                            matches += 1
                            break

                if total > 0:
                    similarity[i][j] = matches / total

        # Find groups of similar measures
        used = set()
        for i in range(n):
            if i not in used:
                group = [i]
                used.add(i)
                for j in range(i + 1, n):
                    if similarity[i][j] >= threshold:
                        group.append(j)
                        used.add(j)
                if len(group) > 1:
                    similar_groups.append(group)

        return similar_groups

    def get_pattern_statistics(self, pattern: Pattern) -> Dict:
        """Krijg statistieken van een pattern."""
        return self.analyze_pattern(
            [hit for measure in pattern.measures for hit in measure.hits],
            pattern.measures
        )
