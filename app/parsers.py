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
		self.start_year = int(request.args.get('start_year', '0'))
		self.start_month = int(request.args.get('start_month', '0'))
		self.end_year = int(request.args.get('end_year', '0'))
		self.end_month = int(request.args.get('end_month', '0'))
		self.style = style

	def start_of_range(self):
		if self.start_year and self.start_month:
			return datetime(year=self.start_year, month=self.start_month, day=1)
		else:
			if self.style == RequestLengthStyle.DEFAULT_YEAR:
				now = datetime.now()
				start_year = now.year-1
				start_month = now.month
				return datetime(year=start_year, month=start_month, day=1)
			elif self.style == RequestLengthStyle.DEFAULT_ALL:
				first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
				return first_entry.entry_date

	def end_of_range(self):
		if self.end_year and self.end_month:
			return datetime(year=self.end_year, month=self.end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1)
		else:
			if self.style == RequestLengthStyle.DEFAULT_YEAR:
				now = datetime.now()
				end_year = now.year
				end_month = now.month
				return datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1)
			elif self.style == RequestLengthStyle.DEFAULT_ALL:
				first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
				return first_entry.entry_date

	def template_args(self):
		template_args = {}
		template_args['start_of_range'] = self.start_of_range()
		template_args['end_of_range'] = self.end_of_range()
		template_args['years'] = self._calculate_years_for_selector()
		return template_args

	def _calculate_years_for_selector(self):
	    first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
	    years = []
	    for year in range(first_entry.entry_date.year, datetime.now().year+1):
	        years.append(year)

	    return years

