import re
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

# Gmail-style tokens recognized in the search box: name:, place:, after:, before:,
# on:, older_than:, newer_than:. Everything else is left as free-text keywords and
# handed to Postgres' websearch_to_tsquery, which already understands quoted phrases,
# "-exclude", and "OR" on its own.
_TOKEN_RE = re.compile(
	r'(?P<key>name|place|after|before|on|older_than|newer_than):(?P<value>"[^"]*"|\S+)',
	re.IGNORECASE,
)

_RELATIVE_RE = re.compile(r'^(?P<amount>\d+)(?P<unit>[dmy])$')

_DATE_FORMATS_BY_PARTS = {
	1: '%Y',
	2: '%Y-%m',
	3: '%Y-%m-%d',
}


def _strip_quotes(value):
	if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
		return value[1:-1]
	return value


def _parse_date_token(value):
	"""Parse a date token's value into (start, end) inclusive bounds - end is the same
	as start for a full YYYY-MM-DD, or the last day of the period for a bare year/month,
	so "on:2023" can match the whole year. Returns None if it doesn't look like a date."""
	value = _strip_quotes(value).replace('/', '-')
	parts = value.split('-')
	if len(parts) not in _DATE_FORMATS_BY_PARTS or not all(p.isdigit() for p in parts):
		return None

	try:
		year = int(parts[0])
		month = int(parts[1]) if len(parts) >= 2 else 1
		day = int(parts[2]) if len(parts) >= 3 else 1
		start = date(year, month, day)
	except ValueError:
		return None

	if len(parts) == 1:
		end = start + relativedelta(years=1) - timedelta(days=1)
	elif len(parts) == 2:
		end = start + relativedelta(months=1) - timedelta(days=1)
	else:
		end = start
	return start, end


def _parse_relative_token(value, today):
	"""Parse an older_than:/newer_than: value like "2y", "6m", or "10d" into a cutoff
	date relative to today - mirrors Gmail's older_than:/newer_than: search operators."""
	match = _RELATIVE_RE.match(_strip_quotes(value).lower())
	if not match:
		return None

	amount = int(match.group('amount'))
	unit = match.group('unit')
	if unit == 'd':
		return today - timedelta(days=amount)
	if unit == 'm':
		return today - relativedelta(months=amount)
	return today - relativedelta(years=amount)


def parse(query_text, today=None):
	"""Parse a Gmail-style journal search query into structured filters:
	{"names": [...], "places": [...], "after": date|None, "before": date|None, "keywords": "..."}.
	after/before are inclusive bounds on entry_date, already merged from any mix of
	after:/before:/on:/older_than:/newer_than: tokens. "keywords" is the leftover free
	text, meant to be passed to websearch_to_tsquery as-is."""
	today = today or date.today()

	names, places = [], []
	after, before = None, None

	def consume(match):
		nonlocal after, before
		key = match.group('key').lower()
		value = match.group('value')

		if key == 'name':
			names.append(_strip_quotes(value))
		elif key == 'place':
			places.append(_strip_quotes(value))
		elif key in ('after', 'before', 'on'):
			bounds = _parse_date_token(value)
			if bounds:
				start, end = bounds
				if key in ('after', 'on'):
					after = max(after, start) if after else start
				if key in ('before', 'on'):
					before = min(before, end) if before else end
		elif key == 'older_than':
			cutoff = _parse_relative_token(value, today)
			if cutoff:
				before = min(before, cutoff) if before else cutoff
		elif key == 'newer_than':
			cutoff = _parse_relative_token(value, today)
			if cutoff:
				after = max(after, cutoff) if after else cutoff

		return ''

	keywords = _TOKEN_RE.sub(consume, query_text).strip()
	keywords = re.sub(r'\s+', ' ', keywords)

	return {
		'names': names,
		'places': places,
		'after': after,
		'before': before,
		'keywords': keywords,
	}
