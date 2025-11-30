import argparse
import logging
import os
from pathlib import Path

try:
    from .config import load_config
    from .pipeline import HelplinePipeline
except ImportError:
    from config import load_config
    from pipeline import HelplinePipeline


def setup_logging(verbose: bool, logs_dir: Path) -> None:
	level = logging.DEBUG if verbose else getattr(logging, os.getenv("LOG_LEVEL", "INFO"), logging.INFO)
	logs_dir.mkdir(parents=True, exist_ok=True)
	log_file = logs_dir / "pipeline.log"
	logging.basicConfig(
		level=level,
		format="%(asctime)s - %(levelname)s - %(message)s",
		handlers=[
			logging.StreamHandler(),
			logging.FileHandler(log_file, encoding="utf-8"),
		],
	)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="AI-Powered Helpline Data Pipeline")
	parser.add_argument("input_file", help="Path to input audio file")
	parser.add_argument("--output", "-o", default="response.wav", help="Output audio file name")
	parser.add_argument("--source-lang", default=os.getenv("DEFAULT_SOURCE_LANG", "auto"))
	parser.add_argument("--target-lang", default=os.getenv("DEFAULT_TARGET_LANG", "en"))
	parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	project_root = Path(__file__).resolve().parent
	output_dir = project_root / "output"
	temp_dir = project_root / "temp"
	logs_dir = project_root / "logs"
	output_dir.mkdir(parents=True, exist_ok=True)
	temp_dir.mkdir(parents=True, exist_ok=True)

	setup_logging(verbose=args.verbose, logs_dir=logs_dir)
	logger = logging.getLogger("ai-helpline-pipeline")

	if not Path(args.input_file).exists():
		logger.error("Input audio file not found: %s", args.input_file)
		raise SystemExit(1)

	config = load_config()
	pipeline = HelplinePipeline(config=config, logger=logger)

	logger.info("AI-Powered Helpline Pipeline Started")
	logger.info("Input file: %s", args.input_file)

	result = pipeline.process_audio(
		audio_path=args.input_file,
		source_lang=args.source_lang,
		target_lang=args.target_lang,
	)

	output_path = output_dir / args.output
	with open(output_path, "wb") as f:
		f.write(result.output_audio_bytes)

	logger.info("Audio file created: %s (%d bytes)", output_path.name, output_path.stat().st_size)
	logger.info("Processing complete! Response saved to %s", output_path)


if __name__ == "__main__":
	main()
