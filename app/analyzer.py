import logging
import re
import spacy
import string
import threading
import time

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
		super().__init__()

	def _load_known_names(self):
		from app.models import KnownName
		return {known_name.name.lower() for known_name in KnownName.query.all()}

	def _load_known_locations(self):
		from app.models import KnownLocation
		return {known_location.location.lower() for known_location in KnownLocation.query.all()}

	def run(self):
		for entry in self.entries:
			self._analyze(entry)
			self.entries_analyzed += 1
			self.percent_complete = float(self.entries_analyzed) / float(self.total_entries_to_analyze)
		db.session.commit()
		if self.total_entries_to_analyze == 0:
			self.percent_complete = float(1) / float(1)

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

	def _entities(self, doc, entry_text):
		names = []
		locations = []
		matched_spans = []
		for ent in doc.ents:
			matched_spans.append((ent.start_char, ent.end_char))
			if ent.text.lower() in self.known_names:
				# a known name always wins, even if spaCy mistagged it as a place
				names.append(self._normalize_name(ent.text))
			elif ent.label_ in PERSON_LABELS:
				names.append(self._normalize_name(ent.text))
			elif ent.label_ in LOCATION_LABELS and self._is_recognized_location(ent.text):
				locations.append(ent.text)
		names.extend(self._normalize_name(name) for name in self._unrecognized_known_names(entry_text, matched_spans))
		locations.extend(self._unrecognized_known_locations(entry_text, matched_spans))
		return names, locations

	@staticmethod
	def _normalize_name(text):
		"""Title-case names so "Alex", "alex", and "ALEX" all count as the same person."""
		return text.strip().title()

	def _is_recognized_location(self, text):
		"""A location only counts if it's a real place (country/US state/city), or
		one you've manually added as a Known Location - filters out spaCy mistagging
		things like brand names ("Alamofire") or business names ("Phat Philly") as places."""
		return text.lower() in self.known_locations or is_real_location(text)

	def _unrecognized_known_names(self, entry_text, matched_spans):
		"""Known names spaCy didn't tag as any entity at all still count as names."""
		return self._unrecognized_known(entry_text, matched_spans, self.known_names)

	def _unrecognized_known_locations(self, entry_text, matched_spans):
		"""Known locations spaCy didn't tag as any entity at all still count as locations."""
		return self._unrecognized_known(entry_text, matched_spans, self.known_locations)

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
