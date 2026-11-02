"""
Command Line Interface voor MIDI Drum Generator.

Gebruik:
    python -m midi_drum_generator.cli [commando] [opties]

Commands:
    analyze    - Analyseer een MIDI-bestand
    generate   - Genereer een nieuw drum pattern
    export     - Exporteer een pattern naar MIDI
    reaper     - Integreer met Reaper
"""

import argparse
import sys
import os
import logging
from typing import Optional

# Voeg de parent directory toe aan path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from midi_drum_generator.midi_analyzer import MIDIAnalyzer
from midi_drum_generator.drum_generator import DrumGenerator, GenerationConfig
from midi_drum_generator.reaper_integration import ReaperIntegration
from midi_drum_generator.utils import setup_logging, validate_midi_file

logger = logging.getLogger(__name__)

def main():
    """Hoofd CLI functie."""
    setup_logging(logging.INFO)

    parser = argparse.ArgumentParser(
        description="MIDI Drum Generator - Genereer drum patterns gebaseerd op bestaande MIDI-bestanden",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  %(prog)s analyze input.mid
  %(prog)s generate input.mid output.mid --measures 8
  %(prog)s generate input.mid output.mid --variation 0.5 --complexity 0.7
  %(prog)s reaper input.mid
  %(prog)s reaper install
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commando')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyseer een MIDI-bestand')
    analyze_parser.add_argument('input', help='Input MIDI-bestand')
    analyze_parser.add_argument('--output', '-o', help='Output bestand voor analyse resultaten')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Genereer een nieuw drum pattern')
    generate_parser.add_argument('input', help='Input MIDI-bestand (bron pattern)')
    generate_parser.add_argument('output', help='Output MIDI-bestand')
    generate_parser.add_argument('--measures', '-m', type=int, default=8,
                                  help='Aantal maten (default: 8)')
    generate_parser.add_argument('--variation', '-v', type=float, default=0.3,
                                  help='Variatie (0-1, default: 0.3)')
    generate_parser.add_argument('--complexity', '-c', type=float, default=0.5,
                                  help='Complexiteit (0-1, default: 0.5)')
    generate_parser.add_argument('--seed', type=int, help='Random seed')
    generate_parser.add_argument('--random', action='store_true',
                                  help='Genereer een compleet willekeurig pattern')

    # Reaper commands
    reaper_parser = subparsers.add_parser('reaper', help='Reaper integratie')
    reaper_subparsers = reaper_parser.add_subparsers(dest='reaper_command', help='Reaper commando')

    # reaper generate
    reaper_gen_parser = reaper_subparsers.add_parser('generate', help='Genereer en importeer in Reaper')
    reaper_gen_parser.add_argument('input', help='Input MIDI-bestand')
    reaper_gen_parser.add_argument('--measures', '-m', type=int, default=8,
                                    help='Aantal maten')

    # reaper import
    reaper_imp_parser = reaper_subparsers.add_parser('import', help='Importeer MIDI in Reaper')
    reaper_imp_parser.add_argument('input', help='MIDI-bestand om te importeren')
    reaper_imp_parser.add_argument('--name', '-n', default='Drum Generator',
                                    help='Naam van de track')

    # reaper install
    reaper_install_parser = reaper_subparsers.add_parser('install',
                                                         help='Installeer ReaScript')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'analyze':
            cmd_analyze(args)
        elif args.command == 'generate':
            cmd_generate(args)
        elif args.command == 'reaper':
            cmd_reaper(args)
        else:
            parser.print_help()
    except Exception as e:
        logger.error(f"Fout: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def cmd_analyze(args) -> None:
    """Analyseer een MIDI-bestand."""
    input_file = args.input

    if not os.path.exists(input_file):
        logger.error(f"Bestand niet gevonden: {input_file}")
        sys.exit(1)

    if not validate_midi_file(input_file):
        logger.error(f"Ongeldig MIDI-bestand: {input_file}")
        sys.exit(1)

    analyzer = MIDIAnalyzer()
    patterns = analyzer.extract_patterns(input_file)

    if not patterns:
        logger.error("Geen drum patterns gevonden")
        sys.exit(1)

    pattern = patterns[0]
    stats = analyzer.get_pattern_statistics(pattern)

    print(f"\n=== Analyse Resultaten ===")
    print(f"Bron: {input_file}")
    print(f"Tempo: {stats['tempo']:.2f} BPM")
    print(f"Tijdsignatuur: {stats['time_signature'][0]}/{stats['time_signature'][1]}")
    print(f"Totaal aantal hits: {stats['total_hits']}")
    print(f"Aantal maten: {stats['total_measures']}")
    print(f"Dichtheid: {stats['density']:.2f} hits per maat")
    print(f"\nCategorie verdeling:")
    for category, count in stats['category_counts'].items():
        print(f"  {category}: {count}")

    if args.output:
        with open(args.output, 'w') as f:
            import json
            json.dump(stats, f, indent=2)
        logger.info(f"Resultaten opgeslagen: {args.output}")

def cmd_generate(args) -> None:
    """Genereer een nieuw drum pattern."""
    input_file = args.input
    output_file = args.output

    if not os.path.exists(input_file):
        logger.error(f"Input bestand niet gevonden: {input_file}")
        sys.exit(1)

    if not validate_midi_file(input_file):
        logger.error(f"Ongeldig MIDI-bestand: {input_file}")
        sys.exit(1)

    # Configureer generator
    config = GenerationConfig(
        variation=args.variation,
        complexity=args.complexity,
        seed=args.seed
    )

    generator = DrumGenerator(config)

    if args.random:
        # Genereer willekeurig pattern
        pattern = generator.generate_random_pattern(
            num_measures=args.measures,
            tempo=120.0
        )
    else:
        # Analyseer bron
        analyzer = MIDIAnalyzer()
        patterns = analyzer.extract_patterns(input_file)

        if not patterns:
            logger.error("Geen drum patterns gevonden in bronbestand")
            sys.exit(1)

        source_pattern = patterns[0]

        # Genereer nieuw pattern gebaseerd op bron
        pattern = generator.generate_from_pattern(
            source_pattern,
            num_measures=args.measures
        )

    # Exporteer
    generator.export_to_midi(pattern, output_file)
    logger.info(f"Drum pattern gegenereerd: {output_file}")

    # Toon info
    print(f"\nGegenereerd pattern:")
    print(f"  Naam: {pattern.name}")
    print(f"  Tempo: {pattern.tempo:.2f} BPM")
    print(f"  Tijdsignatuur: {pattern.time_signature[0]}/{pattern.time_signature[1]}")
    print(f"  Aantal maten: {len(pattern.measures)}")
    print(f"  Totaal hits: {sum(len(m.hits) for m in pattern.measures)}")

def cmd_reaper(args) -> None:
    """Reaper integratie commands."""
    reaper_integration = ReaperIntegration()

    if not reaper_integration.is_reaper_available():
        logger.error("Reaper is niet geinstalleerd of niet gevonden")
        sys.exit(1)

    if args.reaper_command == 'generate':
        input_file = args.input

        if not os.path.exists(input_file):
            logger.error(f"Input bestand niet gevonden: {input_file}")
            sys.exit(1)

        if not validate_midi_file(input_file):
            logger.error(f"Ongeldig MIDI-bestand: {input_file}")
            sys.exit(1)

        # Genereer en importeer
        success = reaper_integration.generate_and_import(
            input_file,
            num_measures=args.measures
        )

        if success:
            logger.info("Drum pattern gegenereerd en geimporteerd in Reaper")
        else:
            logger.error("Mislukt om pattern te genereren/importeren")
            sys.exit(1)

    elif args.reaper_command == 'import':
        input_file = args.input

        if not os.path.exists(input_file):
            logger.error(f"Input bestand niet gevonden: {input_file}")
            sys.exit(1)

        success = reaper_integration.import_midi_to_reaper(
            input_file,
            output_track_name=args.name
        )

        if success:
            logger.info(f"MIDI-bestand geimporteerd in Reaper als '{args.name}'")
        else:
            logger.error("Mislukt om MIDI te importeren")
            sys.exit(1)

    elif args.reaper_command == 'install':
        success = reaper_integration.install_reascript()

        if success:
            logger.info("ReaScript geinstalleerd. Herstart Reaper om het script te zien.")
        else:
            logger.error("Mislukt om ReaScript te installeren")
            sys.exit(1)

    else:
        logger.error(f"Onbekend Reaper commando: {args.reaper_command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
