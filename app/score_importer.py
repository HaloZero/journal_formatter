import csv
import io
import logging
import threading
import time

from dateutil import parser as date_parser

from app import app, db
from app.models import JournalEntry

logger = logging.getLogger('journal.score_importer')


def parse_score_csv(file_stream):
	"""Parse a date,score CSV (a potential header row is auto-detected and skipped)
	into a list of (date, score) tuples. Raises ValueError on the first bad row."""
	text = file_stream.read().decode('utf-8-sig')
	rows = [row for row in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in row)]
	if not rows:
		return []

	if _parse_score_row(rows[0]) is None:
		rows = rows[1:]

	parsed = []
	for line_number, row in enumerate(rows, start=2):
		parsed_row = _parse_score_row(row)
		if parsed_row is None:
			raise ValueError("row {} doesn't have a valid date and integer score".format(line_number))
		parsed.append(parsed_row)
	return parsed


def _parse_score_row(row):
	if len(row) < 2:
		return None
	try:
		entry_date = date_parser.parse(row[0].strip()).date()
		score = int(row[1].strip())
		return (entry_date, score)
	except (ValueError, OverflowError):
		return None


class ScoreImporter(threading.Thread):
	def __init__(self, rows):
		self.rows = rows
		self.scores_updated = 0
		self.scores_skipped = 0
		self.percent_complete = 0
		self.total_entries_to_analyze = len(rows)
		super().__init__()

	def run(self):
		with app.app_context():
			start_time = time.time()
			logger.info("Starting score import of %d rows", self.total_entries_to_analyze)
			for index, (entry_date, score) in enumerate(self.rows):
				self._import_score(entry_date, score)
				self.percent_complete = float(index + 1) / float(self.total_entries_to_analyze)
			db.session.commit()
			if self.total_entries_to_analyze == 0:
				self.percent_complete = float(1) / float(1)
			logger.info(
				"Score import complete in %.2fs: %d updated, %d skipped (no matching entry)",
				time.time() - start_time, self.scores_updated, self.scores_skipped)

	def _import_score(self, entry_date, score):
		entry = JournalEntry.query.filter_by(entry_date=entry_date).first()
		if entry is None:
			logger.info("Skipping score for %s: no journal entry for that date", entry_date)
			self.scores_skipped += 1
			return
		entry.daily_score = score
		self.scores_updated += 1
