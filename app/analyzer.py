import logging
import re
import spacy
import string
import threading
import time

from datetime import datetime

from app import app, db
from app.geography import is_real_location

logger = logging.getLogger('journal.analyzer')

PERSON_LABELS = {"PERSON"}
LOCATION_LABELS = {"GPE", "LOC"}

_nlp = None

def _get_nlp():
	"""Lazily load the spaCy model on first use rather than at import time -
	en_core_web_trf takes several seconds to load, which would otherwise slow down
	every app start, dev-server reload, and test run even when nothing analyzes
	an entry."""
	global _nlp
	if _nlp is None:
		model_name = app.config['SPACY_MODEL']
		logger.info("Loading spaCy model '%s'...", model_name)
		start = time.time()
		_nlp = spacy.load(model_name)
		logger.info("Loaded spaCy model '%s' in %.2fs", model_name, time.time() - start)
	return _nlp

class JournalEntryAnalyzer(threading.Thread):
	def __init__(self, entries):
		self.entries = entries
		self.entries_analyzed = 0
		self.percent_complete = 0
		self.total_entries_to_analyze = len(self.entries)
		self.known_names = self._load_known_names()
		self.known_locations = self._load_known_locations()
		self.name_aliases = self._load_name_aliases()
		self.location_aliases = self._load_location_aliases()
		super().__init__()

	def _load_known_names(self):
		from app.models import KnownName
		return {known_name.name.lower() for known_name in KnownName.query.all()}

	def _load_known_locations(self):
		from app.models import KnownLocation
		return {known_location.location.lower() for known_location in KnownLocation.query.all()}

	def _load_name_aliases(self):
		from app.models import NameAlias
		return {alias.alias.lower(): alias.canonical_name for alias in NameAlias.query.all()}

	def _load_location_aliases(self):
		from app.models import LocationAlias
		return {alias.alias.lower(): alias.canonical_location for alias in LocationAlias.query.all()}

	def run(self):
		with app.app_context():
			start_time = time.time()
			logger.info("Starting analysis of %d entries", self.total_entries_to_analyze)
			for entry in self.entries:
				self._analyze(entry)
				self.entries_analyzed += 1
				self.percent_complete = float(self.entries_analyzed) / float(self.total_entries_to_analyze)
			db.session.commit()
			if self.total_entries_to_analyze == 0:
				self.percent_complete = float(1) / float(1)
			logger.info(
				"Analysis complete in %.2fs: %d entries analyzed",
				time.time() - start_time, self.entries_analyzed)

	def _analyze(self, entry):
		"""
		Analyze a specific journal entry

		Adds common useful attributes such as word count, identifying names and locations,
		and sentence count to an entry

		Parameters:
		entry (JournalEntry): the entry to analyze
		"""
		entry_text = entry.entry_text
		doc = _get_nlp()(entry_text)
		names, locations = self._entities(doc, entry_text)
		word_count = self._analyze_word_count(entry_text)
		sentence_count = len(list(doc.sents))

		entry.word_count = word_count
		entry.sentence_count = sentence_count
		entry.names = names
		entry.locations = locations
		entry.analyzed_at = datetime.utcnow()

	def _entities(self, doc, entry_text):
		names = []
		locations = []
		matched_spans = []
		for ent in doc.ents:
			matched_spans.append((ent.start_char, ent.end_char))
			if ent.text.lower() in self.known_names or ent.text.lower() in self.name_aliases:
				# a known name or alias always wins, even if spaCy mistagged it as a place
				names.append(self._normalize_name(ent.text))
			elif ent.label_ in PERSON_LABELS:
				names.append(self._normalize_name(ent.text))
			elif ent.label_ in LOCATION_LABELS and self._is_recognized_location(ent.text):
				locations.append(self._normalize_location(ent.text))
		names.extend(self._normalize_name(name) for name in self._unrecognized_known_names(entry_text, matched_spans))
		locations.extend(self._normalize_location(location) for location in self._unrecognized_known_locations(entry_text, matched_spans))
		return names, locations

	def _normalize_name(self, text):
		"""Title-case names so "Alex", "alex", and "ALEX" all count as the same person,
		then fold known aliases ("Bob" -> "Robert") onto their canonical name."""
		stripped = text.strip()
		alias = self.name_aliases.get(stripped.lower())
		return alias if alias else stripped.title()

	def _normalize_location(self, text):
		"""Fold known aliases ("SF" -> "San Francisco") onto their canonical location.
		Unlike names, locations aren't title-cased - many (NYC, SF) aren't proper title case."""
		stripped = text.strip()
		return self.location_aliases.get(stripped.lower(), stripped)

	def _is_recognized_location(self, text):
		"""A location only counts if it's a real place (country/US state/city), one you've
		manually added as a Known Location, or a declared location alias - filters out spaCy
		mistagging things like brand names ("Alamofire") or business names ("Phat Philly") as places."""
		return (text.lower() in self.known_locations
			or text.lower() in self.location_aliases
			or is_real_location(text))

	def _unrecognized_known_names(self, entry_text, matched_spans):
		"""Known names or aliases spaCy didn't tag as any entity at all still count as names."""
		return self._unrecognized_known(entry_text, matched_spans, self.known_names | self.name_aliases.keys())

	def _unrecognized_known_locations(self, entry_text, matched_spans):
		"""Known locations or aliases spaCy didn't tag as any entity at all still count as locations."""
		return self._unrecognized_known(entry_text, matched_spans, self.known_locations | self.location_aliases.keys())

	def _unrecognized_known(self, entry_text, matched_spans, known_values):
		found = []
		for known_value in known_values:
			pattern = r'\b' + re.escape(known_value) + r'\b'
			for match in re.finditer(pattern, entry_text, re.IGNORECASE):
				if not any(match.start() < end and match.end() > start for start, end in matched_spans):
					found.append(match.group(0))
		return found

	def _analyze_word_count(self, entry_text):
		words = entry_text.split()
		# create table of stripped entry
		table = str.maketrans('', '', string.punctuation)
		stripped = list(filter(None, [w.translate(table) for w in words]))
		return len(stripped)
