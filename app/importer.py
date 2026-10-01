import logging
import threading
import time

from app import app, db, models
from datetime import datetime
from typing import Protocol

logger = logging.getLogger('journal.importer')

class JournalRecord(Protocol):
	def entryDate():
		raise NotImplementedError

	def entryText():
		raise NotImplementedError

class JournalImporter(threading.Thread):
	def __init__(self, entries: [JournalRecord]):
		self.entries = entries
		self.entries_imported = 0
		self.percent_complete = 0
		self.total_entries_to_analyze = len(self.entries)
		super().__init__()

	def run(self):
		with app.app_context():
			start_time = time.time()
			logger.info("Starting import of %d entries", self.total_entries_to_analyze)
			for entry in self.entries:
				self._import(entry)
				self.entries_imported += 1
				self.percent_complete = float(self.entries_imported) / float(self.total_entries_to_analyze)
			if self.total_entries_to_analyze == 0:
				self.percent_complete = float(1) / float(1)
			db.session.commit()
			logger.info(
				"Import complete in %.2fs: %d entries imported",
				time.time() - start_time, self.entries_imported)

	def _import(self, entry: JournalRecord):
		entry_date = entry.entryDate()
		if models.JournalEntry.query.filter_by(entry_date=entry_date).first():
			return

		new_entry = models.JournalEntry(entry_text=entry.entryText(), entry_date=entry_date)
		db.session.add(new_entry)

class DailyDiaryJournalEntry(JournalRecord):
	def __init__(self, json):
		self.json = json

	def entryDate(self):
		# .date() matters here, not just style: entry_date is a Date column, and the
		# dedup check in JournalImporter._import does filter_by(entry_date=entry_date) -
		# a datetime with a non-midnight time never matches an existing Date row, so a
		# re-import would silently defeat its own duplicate check and double every entry.
		return datetime.strptime(self.json['d'], '%Y-%m-%dT%H:%M:%S').date()

	def entryText(self):
		return self.json['j']

	@staticmethod
	def mapFromJSON(json):
		answers = json['answers']
		entries = []
		for answer in answers:
			entries.append(DailyDiaryJournalEntry(answer))

		return entries