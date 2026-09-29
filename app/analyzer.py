import spacy
import string
import threading

from app import app, db

_nlp = spacy.load(app.config['SPACY_MODEL'])

PERSON_LABELS = {"PERSON"}
LOCATION_LABELS = {"GPE", "LOC"}

class JournalEntryAnalyzer(threading.Thread):
	def __init__(self, entries):
		self.entries = entries
		self.entries_analyzed = 0
		self.percent_complete = 0
		self.total_entries_to_analyze = len(self.entries)
		super().__init__()

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
		doc = _nlp(entry_text)
		names, locations = self._entities(doc)
		word_count = self._analyze_word_count(entry_text)
		sentence_count = len(list(doc.sents))

		entry.word_count = word_count
		entry.sentence_count = sentence_count
		entry.names = names
		entry.locations = locations

	def _entities(self, doc):
		names = []
		locations = []
		for ent in doc.ents:
			if ent.label_ in PERSON_LABELS:
				names.append(ent.text)
			elif ent.label_ in LOCATION_LABELS:
				locations.append(ent.text)
		return names, locations

	def _analyze_word_count(self, entry_text):
		words = entry_text.split()
		# create table of stripped entry
		table = str.maketrans('', '', string.punctuation)
		stripped = list(filter(None, [w.translate(table) for w in words]))
		return len(stripped)
