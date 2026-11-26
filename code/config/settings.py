"""
Configuration and settings for the SDG Credibility Framework.
Loads API keys from .env file and defines framework constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys ---
LANDINGAI_API_KEY = os.getenv("LANDINGAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# agentic-doc v0.3+ expects VISION_AGENT_API_KEY; sync from LANDINGAI_API_KEY
if LANDINGAI_API_KEY and not os.getenv("VISION_AGENT_API_KEY"):
    os.environ["VISION_AGENT_API_KEY"] = LANDINGAI_API_KEY

# --- Model Settings ---
PRIMARY_MODEL = "gpt-4o"
SCORING_TEMPERATURE = 0.3  # Low but non-zero for 3-run median scoring
SCORING_RUNS = 3           # Number of independent scoring runs per claim
CONFIDENCE_THRESHOLD = 0.5 # Minimum confidence for SDG target mapping

# --- Credibility Scoring ---
CREDIBILITY_DIMENSIONS = ["specificity", "measurability", "temporality", "evidence", "consistency"]
SCORE_RANGE = (0, 3)
TIER_THRESHOLDS = {
    "symbolic": (0.0, 1.0),           # CS < 1.0
    "partially_substantive": (1.0, 2.0), # 1.0 <= CS < 2.0
    "substantive": (2.0, 3.0),        # CS >= 2.0
}

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Ensure output directory exists
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_keys():
    """Check that required API keys are set."""
    missing = []
    if not LANDINGAI_API_KEY:
        missing.append("LANDINGAI_API_KEY")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if missing:
        print(f"WARNING: Missing API keys: {', '.join(missing)}")
        print("Copy .env.example to .env and add your keys.")
        return False
    return True
