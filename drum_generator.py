"""
Drum Generator Module

Genereert nieuwe drum patterns gebaseerd op geanalyseerde patronen.
"""

import random
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from copy import deepcopy
import logging

from .midi_analyzer import DrumHit, Measure, Pattern, DRUM_NOTE_NAMES, DRUM_CATEGORIES

logger = logging.getLogger(__name__)

@dataclass
class GenerationConfig:
    """Configuratie voor drum pattern generatie."""
    # Variatie parameters
    variation: float = 0.3  # 0-1, hoeveel variatie toe te staan
    complexity: float = 0.5  # 0-1, complexiteit van het pattern
    density: float = 0.7  # 0-1, dichtheid van hits

    # Category weights (probabiliteit per categorie)
    category_weights: Dict[str, float] = field(default_factory=lambda: {
        "kick": 1.0,
        "snare": 1.0,
        "tom": 0.5,
        "hi_hat": 1.5,
        "cymbal": 0.8,
        "percussion": 0.2
    })

    # Tempo variatie
    tempo_variation: float = 5.0  # BPM variatie

    # Maat structuur
    repeat_measures: bool = True  # Herhaal maten
    max_measures: int = 16  # Maximaal aantal maten

    # Random seed
    seed: Optional[int] = None

class DrumGenerator:
    """
    Genereert drum patterns gebaseerd op bestaande patronen.
    """

    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()
        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)

        # Voorbereide data
        self._category_notes: Dict[str, List[int]] = DRUM_CATEGORIES
        self._all_drum_notes: List[int] = list(DRUM_NOTE_NAMES.keys())

    def _select_random_note(self, category: str) -> int:
        """Selecteer een willekeurige note uit een categorie."""
        notes = self._category_notes.get(category, [])
        if not notes:
            notes = self._all_drum_notes
        return random.choice(notes)

    def _select_category(self) -> str:
        """Selecteer een willekeurige categorie gebaseerd op weights."""
        categories = list(self.config.category_weights.keys())
        weights = list(self.config.category_weights.values())
        return random.choices(categories, weights=weights, k=1)[0]

    def _generate_random_hit(self, time: float, measure_duration: float) -> DrumHit:
        """Genereer een willekeurige drum hit."""
        category = self._select_category()
        note = self._select_random_note(category)
        velocity = random.randint(60, 120)

        return DrumHit(
            note=note,
            velocity=velocity,
            time=time,
            category=category,
            name=DRUM_NOTE_NAMES.get(note, f"Unknown ({note})")
        )

    def _mutate_hit(self, hit: DrumHit, mutation_rate: float = 0.3) -> DrumHit:
        """Muteer een drum hit."""
        if random.random() < mutation_rate:
            # Change note within category
            category = hit.category
            notes = self._category_notes.get(category, self._all_drum_notes)
            if len(notes) > 1:
                new_note = random.choice([n for n in notes if n != hit.note])
                hit = DrumHit(
                    note=new_note,
                    velocity=hit.velocity,
                    time=hit.time,
                    category=category,
                    name=DRUM_NOTE_NAMES.get(new_note, hit.name)
                )

        if random.random() < mutation_rate:
            # Change velocity
            velocity_change = random.randint(-20, 20)
            new_velocity = max(1, min(127, hit.velocity + velocity_change))
            hit = DrumHit(
                note=hit.note,
                velocity=new_velocity,
                time=hit.time,
                category=hit.category,
                name=hit.name
            )

        if random.random() < mutation_rate / 2:
            # Change time slightly
            time_change = random.uniform(-0.05, 0.05)
            hit = DrumHit(
                note=hit.note,
                velocity=hit.velocity,
                time=max(0, hit.time + time_change),
                category=hit.category,
                name=hit.name
            )

        return hit

    def _mutate_measure(self, measure: Measure, mutation_rate: float = 0.3) -> Measure:
        """Muteer een maat."""
        new_hits = []

        for hit in measure.hits:
            if random.random() < mutation_rate:
                # Remove hit
                continue
            new_hits.append(self._mutate_hit(hit, mutation_rate))

        # Add new random hits
        if random.random() < mutation_rate:
            num_new_hits = random.randint(1, 3)
            for _ in range(num_new_hits):
                time = random.uniform(0, measure.duration)
                new_hits.append(self._generate_random_hit(time, measure.duration))

        return Measure(
            start_time=measure.start_time,
            end_time=measure.end_time,
            tempo=measure.tempo,
            hits=new_hits
        )

    def generate_from_pattern(self, pattern: Pattern, num_measures: int = 8) -> Pattern:
        """Genereer een nieuw pattern gebaseerd op een bestaand pattern."""
        if not pattern.measures:
            return self.generate_random_pattern(num_measures)

        # Select random measures from the original pattern
        source_measures = pattern.measures
        selected_measures = []

        for _ in range(num_measures):
            # Select a random measure
            source_measure = random.choice(source_measures)

            # Mutate it
            mutated_measure = self._mutate_measure(
                source_measure,
                self.config.variation
            )

            # Adjust time
            measure_index = len(selected_measures)
            measure_duration = source_measure.duration
            mutated_measure = Measure(
                start_time=measure_index * measure_duration,
                end_time=(measure_index + 1) * measure_duration,
                tempo=pattern.tempo + random.uniform(-self.config.tempo_variation, self.config.tempo_variation),
                hits=mutated_measure.hits
            )

            selected_measures.append(mutated_measure)

        # Generate new pattern name
        pattern_name = f"Generated from {pattern.name}"

        return Pattern(
            name=pattern_name,
            measures=selected_measures,
            tempo=pattern.tempo,
            time_signature=pattern.time_signature
        )

    def generate_random_measure(self, measure_index: int, measure_duration: float,
                                tempo: float) -> Measure:
        """Genereer een willekeurige maat."""
        start_time = measure_index * measure_duration
        end_time = (measure_index + 1) * measure_duration

        # Determine number of hits based on density
        max_hits = int(measure_duration * 10)  # Max 10 hits per second
        num_hits = random.randint(1, max_hits)

        # Adjust based on complexity
        num_hits = int(num_hits * self.config.complexity)

        hits = []
        for _ in range(num_hits):
            time = random.uniform(start_time, end_time)
            hit = self._generate_random_hit(time, measure_duration)
            hits.append(hit)

        return Measure(
            start_time=start_time,
            end_time=end_time,
            tempo=tempo,
            hits=hits
        )

    def generate_random_pattern(self, num_measures: int = 8, tempo: float = 120.0,
                               time_signature: Tuple[int, int] = (4, 4)) -> Pattern:
        """Genereer een compleet willekeurig drum pattern."""
        numerator, denominator = time_signature
        beat_duration = 60.0 / tempo
        measure_duration = numerator * beat_duration

        measures = []
        for i in range(num_measures):
            measure = self.generate_random_measure(i, measure_duration, tempo)
            measures.append(measure)

        return Pattern(
            name="Random Pattern",
            measures=measures,
            tempo=tempo,
            time_signature=time_signature
        )

    def _get_category_from_note(self, note: int) -> str:
        """Bepaal categorie van een note."""
        for category, notes in DRUM_CATEGORIES.items():
            if note in notes:
                return category
        return "unknown"

    def add_variation(self, pattern: Pattern, variation_amount: float = 0.3) -> Pattern:
        """Voeg variatie toe aan een bestaand pattern."""
        new_measures = []

        for i, measure in enumerate(pattern.measures):
            new_measure = self._mutate_measure(measure, variation_amount)
            new_measure = Measure(
                start_time=measure.start_time,
                end_time=measure.end_time,
                tempo=pattern.tempo + random.uniform(-self.config.tempo_variation, self.config.tempo_variation),
                hits=new_measure.hits
            )
            new_measures.append(new_measure)

        return Pattern(
            name=f"{pattern.name} (Varied)",
            measures=new_measures,
            tempo=pattern.tempo,
            time_signature=pattern.time_signature
        )

    def export_to_midi(self, pattern: Pattern, output_path: str) -> str:
        """Exporteer een pattern naar een MIDI-bestand."""
        import mido
        from mido import MidiFile, MidiTrack, Message, MetaMessage

        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)

        # Set tempo
        microseconds_per_beat = int(60000000.0 / pattern.tempo)
        track.append(MetaMessage('set_tempo', tempo=microseconds_per_beat, time=0))

        # Set time signature
        numerator, denominator = pattern.time_signature
        track.append(MetaMessage('time_signature', numerator=numerator, denominator=denominator, time=0))

        # Add all notes
        ticks_per_beat = mid.ticks_per_beat

        # Sort all hits by time
        all_hits = []
        for measure in pattern.measures:
            all_hits.extend(measure.hits)

        all_hits.sort(key=lambda h: h.time)

        # Convert times to ticks
        beat_duration_ticks = ticks_per_beat

        prev_time_ticks = 0
        for hit in all_hits:
            time_ticks = int(hit.time * ticks_per_beat * pattern.tempo / 60.0)
            delta_time = time_ticks - prev_time_ticks
            prev_time_ticks = time_ticks

            # Note on
            track.append(Message('note_on', note=hit.note, velocity=hit.velocity,
                               time=delta_time, channel=9))

            # Note off (short duration for drums)
            track.append(Message('note_off', note=hit.note, velocity=0,
                               time=10, channel=9))

        # Save
        mid.save(output_path)
        logger.info(f"Pattern geexporteerd naar {output_path}")
        return output_path
