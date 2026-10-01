from datetime import date

from app import models
from app.importer import JournalImporter, DailyDiaryJournalEntry


class FakeRecord:
	def __init__(self, entry_date, entry_text):
		self._entry_date = entry_date
		self._entry_text = entry_text

	def entryDate(self):
		return self._entry_date

	def entryText(self):
		return self._entry_text


def test_import_skips_duplicate_entries_for_existing_date():
	JournalImporter([FakeRecord(date(2020, 1, 1), "first pass")]).run()
	JournalImporter([FakeRecord(date(2020, 1, 1), "second pass")]).run()

	entries = models.JournalEntry.query.filter_by(entry_date=date(2020, 1, 1)).all()
	assert len(entries) == 1
	assert entries[0].entry_text == "first pass"


def test_daily_diary_entry_date_is_a_plain_date_not_a_datetime():
	record = DailyDiaryJournalEntry({'d': '2013-10-01T14:32:07', 'j': 'entry text'})
	assert record.entryDate() == date(2013, 10, 1)


def test_reimporting_same_daily_diary_export_does_not_duplicate_entries():
	# regression test: entryDate() used to return a full datetime (with the diary
	# app's real, non-midnight time-of-day), which made the dedup check in
	# JournalImporter._import silently fail to match the existing Date-column row,
	# so re-running an import duplicated every entry in the export.
	entry_json = {'d': '2013-10-01T14:32:07', 'j': 'entry text'}

	JournalImporter(DailyDiaryJournalEntry.mapFromJSON({'answers': [entry_json]})).run()
	JournalImporter(DailyDiaryJournalEntry.mapFromJSON({'answers': [entry_json]})).run()

	assert models.JournalEntry.query.filter_by(entry_date=date(2013, 10, 1)).count() == 1
