from datetime import date

from tests.factories import make_journal_entry, make_journal_photo
from app.parsers import DateRangeParser, RequestLengthStyle
from app.presenters import DateStyle, NamesPresenter, LocationTimelinePresenter, SentimentBucketPresenter


class MockRequest:
	def __init__(self, args=None):
		self.args = args or {}


def test_names_presenter_buckets_by_day():
	make_journal_entry(entry_date=date(2020, 1, 1), names=["Sarah", "Marco"])
	make_journal_entry(entry_date=date(2020, 1, 1), names=["Sarah"])
	make_journal_entry(entry_date=date(2020, 1, 2), names=["Marco"])

	entries = _all_entries()
	buckets = NamesPresenter(entries).bucket_info(DateStyle.DAY)

	assert buckets["Sarah"]["01-01-2020"] == 2
	assert buckets["Marco"]["01-01-2020"] == 1
	assert buckets["Marco"]["02-01-2020"] == 1


def test_location_timeline_merges_mentions_within_gap():
	make_journal_entry(entry_date=date(2019, 6, 1), locations=["Tokyo"])
	make_journal_entry(entry_date=date(2019, 6, 10), locations=["Tokyo"])

	entries = _all_entries()
	timeline = LocationTimelinePresenter(entries, gap_days=14).timeline()

	assert len(timeline) == 1
	assert timeline[0]['location'] == 'Tokyo'
	assert timeline[0]['start_date'] == date(2019, 6, 1)
	assert timeline[0]['end_date'] == date(2019, 6, 10)
	assert timeline[0]['mention_count'] == 2


def test_location_timeline_splits_mentions_past_gap():
	make_journal_entry(entry_date=date(2019, 6, 1), locations=["Tokyo"])
	make_journal_entry(entry_date=date(2019, 9, 15), locations=["Tokyo"])

	entries = _all_entries()
	timeline = LocationTimelinePresenter(entries, gap_days=14).timeline()

	assert len(timeline) == 2
	assert [r['start_date'] for r in timeline] == [date(2019, 6, 1), date(2019, 9, 15)]


def test_journal_entry_photos_relationship():
	entry = make_journal_entry()
	make_journal_photo(journal_entry=entry, file_path="photos/2020/a.jpg")
	make_journal_photo(journal_entry=entry, file_path="photos/2020/b.jpg")

	assert len(entry.photos) == 2
	assert {p.file_path for p in entry.photos} == {"photos/2020/a.jpg", "photos/2020/b.jpg"}


def test_date_range_parser_default_all_with_no_entries():
	parser = DateRangeParser(MockRequest(), RequestLengthStyle.DEFAULT_ALL)

	assert parser.start_of_range() is not None
	assert parser.end_of_range() is not None
	assert parser.template_args()['years'] == []


def test_sentiment_bucket_presenter_with_no_entries():
	assert SentimentBucketPresenter([]).bucket_info() == {}


def test_sentiment_bucket_presenter_trims_to_populated_buckets():
	entry = make_journal_entry(entry_text="This is wonderful and amazing!")

	buckets = SentimentBucketPresenter([entry]).bucket_info()

	assert sum(buckets.values()) == 1


def _all_entries():
	from app.models import JournalEntry
	return JournalEntry.query.order_by(JournalEntry.entry_date).all()
