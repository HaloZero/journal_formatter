from collections import Counter, OrderedDict
from enum import Enum
import nltk

class DateStyle(Enum):
	YEAR = "%Y"
	MONTH_YEAR = "%m-%Y"
	MONTH = "%m"
	DAY = "%d-%m-%Y"

class SentimentPresenter():
	def __init__(self, entries):
		self.entries = entries

	def bucket_info(self, dateStyle):
		final_buckets = OrderedDict()
		buckets = {}
		entry_amounts = {}
		for entry in self.entries:
			key = entry.entry_date.strftime(dateStyle.value)
			buckets[key] = buckets.get(key, 0) + entry.sentiment().polarity
			entry_amounts[key] = entry_amounts.get(key, 0) + 1

		for key, value in buckets.items():
			final_buckets[key] = value / entry_amounts[key]

		return final_buckets

class SentimentBucketPresenter():
	def __init__(self, entries):
		self.entries = entries

	def bucket_info(self):
		keys = [float(number) / 10 for number in range(-10, 10)] + [1.0]
		buckets = OrderedDict()
		for key in keys:
			buckets[key] = 0
		for entry in self.entries:
			key = round(entry.sentiment().polarity, 1)
			buckets[key] += 1

		# clear all leading and trailing keys
		for key in keys:
			if buckets[key] == 0:
				del buckets[key]
			else:
				break

		for key in reversed(keys):
			if buckets[key] == 0:
				del buckets[key]
			else:
				break

		return buckets

class NGramPresenter():
	def __init__(self, entries):
		self.entries = entries

	def bucket_info(self, n, limit=5):
		buckets = {}
		for entry in self.entries:
			entry_text = entry.entry_text
			sentences_tokenized = nltk.sent_tokenize(entry_text)
			for sentence in sentences_tokenized:
				tokenized_entry = nltk.word_tokenize(str.lower(sentence))
				grammed_entry = nltk.ngrams(tokenized_entry, n)
				for gram in grammed_entry:
					key = " ".join(gram)
					buckets[key] = buckets.get(key, 0) + 1

		return dict(Counter(buckets).most_common(limit))

class WordPresenter():
	def __init__(self, entries):
		self.entries = entries

	def bucket_info(self, dateStyle):
		buckets = OrderedDict()
		for entry in self.entries:
			key = entry.entry_date.strftime(dateStyle.value)
			buckets[key] = buckets.get(key, 0) + entry.unique_word_count()

		return buckets


class NamesPresenter():
	def __init__(self, entries):
		self.entries = entries

	def bucket_info(self, dateStyle):
		names_to_data_sets = {}

		for entry in self.entries:
			key = entry.entry_date.strftime(dateStyle.value)
			names = entry.names or []
			for name in names:
				if names_to_data_sets.get(name) == None:
					names_to_data_sets[name] = OrderedDict()
				names_to_data_sets[name][key] = names_to_data_sets[name].get(key, 0) + 1

		return names_to_data_sets

class LocationTimelinePresenter():
	def __init__(self, entries, gap_days=14):
		self.entries = entries
		self.gap_days = gap_days

	def timeline(self):
		mentions = {}
		for entry in self.entries:
			for location in (entry.locations or []):
				mentions.setdefault(location, []).append(entry.entry_date)

		ranges = []
		for location, dates in mentions.items():
			ranges.extend(self._ranges_for_location(location, sorted(set(dates))))

		ranges.sort(key=lambda r: r['start_date'])
		return ranges

	def _ranges_for_location(self, location, dates):
		ranges = []
		range_start = dates[0]
		range_end = dates[0]
		mention_count = 1

		for date in dates[1:]:
			if (date - range_end).days <= self.gap_days:
				range_end = date
				mention_count += 1
			else:
				ranges.append(self._range(location, range_start, range_end, mention_count))
				range_start = date
				range_end = date
				mention_count = 1

		ranges.append(self._range(location, range_start, range_end, mention_count))
		return ranges

	def _range(self, location, start_date, end_date, mention_count):
		return {
			'location': location,
			'start_date': start_date,
			'end_date': end_date,
			'mention_count': mention_count,
		}