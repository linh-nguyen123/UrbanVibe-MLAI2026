import sys
from pathlib import Path

# Support running this file directly from an editor or terminal.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.models.src.block3.filter import block3_filter


result = block3_filter(
    event_class="Siren",
    confidence=0.82,
    decibel=81.4,
)

print(result)
