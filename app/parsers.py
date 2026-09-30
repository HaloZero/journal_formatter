from app import models
from datetime import datetime
from dateutil.relativedelta import *
from enum import Enum

class RequestLengthStyle(Enum):
	# Default range to last year -> now
	DEFAULT_YEAR = 0
	# Default range ALL entries
	DEFAULT_ALL = 1

class DateRangeParser():
	def __init__(self, request, style: RequestLengthStyle):
		self.start = self._parse_month(request.args.get('start', ''))
		self.end = self._parse_month(request.args.get('end', ''))
		self.style = style

	@staticmethod
	def _parse_month(value):
		# Matches the value format of <input type="month">, e.g. "2020-05".
		try:
			return datetime.strptime(value, '%Y-%m')
		except ValueError:
			return None

	def start_of_range(self):
		if self.start:
			return self.start
		else:
			if self.style == RequestLengthStyle.DEFAULT_YEAR:
				now = datetime.now()
				start_year = now.year-1
				start_month = now.month
				return datetime(year=start_year, month=start_month, day=1)
			elif self.style == RequestLengthStyle.DEFAULT_ALL:
				first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
				return first_entry.entry_date if first_entry else datetime.now()

	def end_of_range(self):
		if self.end:
			return self.end + relativedelta(months=+1) - relativedelta(days=+1)
		else:
			if self.style == RequestLengthStyle.DEFAULT_YEAR:
				now = datetime.now()
				end_year = now.year
				end_month = now.month
				return datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1)
			elif self.style == RequestLengthStyle.DEFAULT_ALL:
				first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date.desc()).first()
				return first_entry.entry_date if first_entry else datetime.now()

	def template_args(self):
		template_args = {}
		template_args['start_of_range'] = self.start_of_range()
		template_args['end_of_range'] = self.end_of_range()
		template_args['years'] = self._calculate_years_for_selector()
		return template_args

	def _calculate_years_for_selector(self):
	    first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
	    if first_entry is None:
	        return []

	    years = []
	    for year in range(first_entry.entry_date.year, datetime.now().year+1):
	        years.append(year)

	    return years

