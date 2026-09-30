from app import models
from datetime import datetime
from dateutil.relativedelta import *
from enum import Enum

class RequestLengthStyle(Enum):
	# Default range to last year -> now
	DEFAULT_YEAR = 0
	# Default range ALL entries
	DEFAULT_ALL = 1

def journal_date_bounds():
	"""Earliest/latest dates a native date picker should allow, as ISO strings."""
	first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
	min_date = first_entry.entry_date.isoformat() if first_entry else None
	max_date = datetime.now().date().isoformat()
	return min_date, max_date

def _parse_date(value):
	if not value:
		return None
	try:
		return datetime.strptime(value, '%Y-%m-%d')
	except ValueError:
		return None

class DateRangeParser():
	def __init__(self, request, style: RequestLengthStyle):
		self.start_date = _parse_date(request.args.get('start_date'))
		self.end_date = _parse_date(request.args.get('end_date'))
		self.style = style

	def start_of_range(self):
		if self.start_date:
			return self.start_date
		if self.style == RequestLengthStyle.DEFAULT_YEAR:
			return datetime.now() - relativedelta(years=1)
		elif self.style == RequestLengthStyle.DEFAULT_ALL:
			first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
			return datetime.combine(first_entry.entry_date, datetime.min.time()) if first_entry else datetime.now()

	def end_of_range(self):
		if self.end_date:
			return self.end_date
		if self.style == RequestLengthStyle.DEFAULT_YEAR:
			return datetime.now()
		elif self.style == RequestLengthStyle.DEFAULT_ALL:
			last_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date.desc()).first()
			return datetime.combine(last_entry.entry_date, datetime.min.time()) if last_entry else datetime.now()

	def template_args(self):
		min_date, max_date = journal_date_bounds()
		return {
			'start_of_range': self.start_of_range(),
			'end_of_range': self.end_of_range(),
			'min_date': min_date,
			'max_date': max_date,
		}
