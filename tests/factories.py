import itertools
from datetime import date, datetime, timedelta

from app import db
from app.models import JournalEntry, JournalPhoto, SentimentRecord

_date_counter = itertools.count()

def make_journal_entry(**overrides):
	defaults = {
		'entry_date': date(2020, 1, 1) + timedelta(days=next(_date_counter)),
		'entry_text': "A fake journal entry for testing.",
		'word_count': 6,
		'sentence_count': 1,
		'names': [],
		'locations': [],
		'daily_score': None,
	}
	defaults.update(overrides)
	entry = JournalEntry(**defaults)
	db.session.add(entry)
	db.session.commit()
	return entry

def make_journal_photo(journal_entry=None, **overrides):
	if journal_entry is None:
		journal_entry = make_journal_entry()

	defaults = {
		'journal_entry_id': journal_entry.id,
		'file_path': 'photos/2020/fake.jpg',
		'caption': None,
		'created_at': datetime(2020, 1, 1),
	}
	defaults.update(overrides)
	photo = JournalPhoto(**defaults)
	db.session.add(photo)
	db.session.commit()
	return photo

def make_sentiment_record(**overrides):
	defaults = {
		'sentence': "This is a fake sentence.",
		'sentiment': 'pos',
	}
	defaults.update(overrides)
	record = SentimentRecord(**defaults)
	db.session.add(record)
	db.session.commit()
	return record
