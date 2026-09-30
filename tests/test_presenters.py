import datetime

from app.parsers import DateRangeParser, RequestLengthStyle
from freezegun import freeze_time

class MockRequest():
	def __init__(self, args):
		self.args = args

def test_parsing():
	request = MockRequest({'start': '2020-05', 'end': '2020-11'})
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

@freeze_time("2020-11-01")
def test_malformed_month_falls_back_to_default():
	request = MockRequest({'start': 'not-a-month', 'end': ''})
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_YEAR)
	assert parser.start_of_range().year == 2019
	assert parser.start_of_range().month == 11
	assert parser.end_of_range().year == 2020
	assert parser.end_of_range().month == 11
