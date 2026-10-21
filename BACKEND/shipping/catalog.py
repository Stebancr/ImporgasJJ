"""Eight-digit codes supplied with TCC's plugin; never truncate to DANE-5."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def cities():
    return json.loads(Path(__file__).with_name('cities.json').read_text(encoding='utf8'))


def city(code):
    return next((item for item in cities() if item['code'] == str(code)), None)
