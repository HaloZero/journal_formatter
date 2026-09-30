import geonamescache

_gc = geonamescache.GeonamesCache()

_PLACE_NAMES = (
	{country['name'].lower() for country in _gc.get_countries().values()}
	| {state['name'].lower() for state in _gc.get_us_states().values()}
	| {city['name'].lower() for city in _gc.get_cities().values()}
)

# Codes (ISO country codes, US state abbreviations) are matched case-sensitively
# so we don't treat common lowercase words that happen to collide with a code
# (e.g. "in", "or", "hi") as real places.
_PLACE_CODES = {state['code'] for state in _gc.get_us_states().values()}
for country in _gc.get_countries().values():
	_PLACE_CODES.add(country['iso'])
	_PLACE_CODES.add(country['iso3'])

def is_real_location(text):
	"""True if text names a real country, US state, or city (population > 15,000)."""
	stripped = text.strip()
	if not stripped:
		return False
	return stripped in _PLACE_CODES or stripped.lower() in _PLACE_NAMES
