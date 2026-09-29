import datetime

from app.parsers import DateRangeParser, RequestLengthStyle
from freezegun import freeze_time

class MockRequest():
	def __init__(self, args):
		self.args = args

def test_parsing():
	request = MockRequest({'start_year': 2020, 'start_month': 5, 'end_year': 2020, 'end_month': 11})
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_YEAR)
	assert parser.start_of_range().month == 5
	assert parser.start_of_range().year == 2020
	assert parser.start_of_range().day == 1
	assert parser.end_of_range().month == 11
	assert parser.end_of_range().year == 2020
	assert parser.end_of_range().day == 30

@freeze_time("2020-11-01")
def test_default_year_parsing():
	request = MockRequest({})
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_YEAR)
	assert parser.start_of_range().month == 11
	assert parser.start_of_range().year == 2019
	assert parser.start_of_range().day == 1
	assert parser.end_of_range().month == 11
	assert parser.end_of_range().year == 2020
	assert parser.end_of_range().day == 30
