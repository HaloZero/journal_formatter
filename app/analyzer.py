import nltk
import string
import threading

from app import db

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

		Adds common useful attributes such as word count, identifying names, and sentence count to an entry

		Parameters:
		entry (JournalEntry): the entry to analyze
		"""
		entry_text = entry.entry_text
		word_count = self._analyze_word_count(entry_text)
		names = self._names(entry.entry_text)
		sentence_count = self._analyze_sentence_count(entry_text)

		entry.word_count = word_count
		entry.sentence_count = sentence_count
		entry.names = names

	def _names(self, entry_text):
		tokenized_words = nltk.word_tokenize(entry_text)
		tagged_words = nltk.pos_tag(tokenized_words)
		filtered_names = list(filter(lambda x: x[1] in ["NNP", "NNPS"], tagged_words))
		return list(map(lambda x: x[0], filtered_names))

	def _analyze_word_count(self, entry_text):
		words = entry_text.split()
		# create table of stripped entry
		table = str.maketrans('', '', string.punctuation)
		stripped = list(filter(None, [w.translate(table) for w in words]))
		return len(stripped)

	def _analyze_sentence_count(self, entry_text):
		return len(nltk.tokenize.sent_tokenize(entry_text))
