"""Eight-digit codes supplied with TCC's plugin; never truncate to DANE-5."""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def cities():
    return json.loads(Path(__file__).with_name('cities.json').read_text(encoding='utf8'))


def city(code):
    return next((item for item in cities() if item['code'] == str(code)), None)


def address_city(address):
    """Resolve legacy names only when unique; never update the saved address."""
    import unicodedata
    def normalized(value):
        return ''.join(char for char in unicodedata.normalize('NFD', str(value)).casefold() if char.isalnum())
    def municipality(value):
        name = normalized(value)
        return 'cali' if name == 'santiagodecali' else name
    if address.tcc_city_code:
        return city(address.tcc_city_code)
    matches = [item for item in cities() if municipality(item['city']) == municipality(address.city)
               and normalized(item['department']) == normalized(address.department)]
    return matches[0] if len(matches) == 1 else None
