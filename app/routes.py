import calendar
import json
import logging
import math
import pdb
import nltk
import random

from flask import render_template, flash, redirect, url_for, request
from pychartjs import Color
from app import app, db, models, charts
from datetime import datetime
from dateutil.relativedelta import *
from sqlalchemy import and_
from sqlalchemy.sql.expression import func
from textblob import TextBlob

from app.classifier import Classifier
from app.presenters import DateStyle, SentimentPresenter, SentimentBucketPresenter, NGramPresenter, WordPresenter, NamesPresenter, LocationTimelinePresenter
from app.analyzer import JournalEntryAnalyzer
from app.importer import DailyDiaryJournalEntry, JournalImporter
from app.photo_importer import PhotoImporter
from app.parsers import DateRangeParser, RequestLengthStyle

logger = logging.getLogger('journal.import')
logger_config = logging.getLogger('journal.config')

# Cap how many name lines get drawn on /names - past this the chart stops being readable
MAX_NAME_SERIES = 15

# /names_comparison consolidates its date range into at most this many time buckets
MAX_COMPARISON_BUCKETS = 20

# Selectable "top N names per bucket" options on /names_comparison
TOP_N_OPTIONS = [10, 25]
DEFAULT_TOP_N = 10
NAME_CHART_COLORS = [
	Color.Red, Color.Blue, Color.Green, Color.Orange, Color.Purple,
	Color.Teal, Color.Maroon, Color.Olive, Color.Navy, Color.Brown,
	Color.Magenta, Color.Cyan, Color.Lime, Color.Pink, Color.Gray,
]

operation_threads = {}

class SelectedDate:
	def __init__(self, year=None, month=None, day=None):
		self.year = year
		self.month = month
		self.day = day

@app.route('/')
def index():
	if models.JournalEntry.query.first() is None:
		return render_template('welcome.html')

	now = datetime.now()
	start_of_month = _parse_month_param('month', datetime(year=now.year, month=now.month, day=1))
	start_of_month, end_of_month = _month_bounds(start_of_month)

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_month,
			models.JournalEntry.entry_date <= end_of_month))

	selected_date = SelectedDate(year=start_of_month.year, month=start_of_month.month)

	return render_template('index.html', entries=entries, selected_date=selected_date)

@app.route('/classify_sentences')
def classify_sentences():
	entries = models.JournalEntry.query.order_by(func.random()).limit(1)
	sentences = nltk.sent_tokenize(entries.first().entry_text)

	return render_template('classify.html', sentences=sentences)

@app.route('/post_classify_sentence', methods=['POST'])
def classify_sentences_post():
	sentence = request.form.get('sentence')
	sentiment = request.form.get('sentiment')

	assert(sentiment == "pos" or sentiment == "neg" or sentiment == "neutral")

	if models.SentimentRecord.query.filter(models.SentimentRecord.sentence==sentence).first() != None:
		return {}

	new_entry = models.SentimentRecord(sentence=sentence, sentiment=sentiment)
	db.session.add(new_entry)
	db.session.commit()

	return {}

@app.route('/day_in_history')
def day_in_history():
	now = datetime.now()
	try:
		parsed_date = datetime.strptime(request.args.get('date', ''), '%Y-%m-%d')
		month, day = parsed_date.month, parsed_date.day
	except ValueError:
		month, day = now.month, now.day

	first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
	valid_dates = []
	if first_entry is not None:
		for year in range(first_entry.entry_date.year, datetime.now().year+1):
			try:
				valid_dates.append(datetime(year=year, month=month, day=day))
			except ValueError:
				continue  # e.g. Feb 29 in a non-leap year

	entries = models.JournalEntry.query.filter(
		models.JournalEntry.entry_date.in_(valid_dates)).order_by(models.JournalEntry.entry_date.desc())
	selected_date = SelectedDate(year=now.year, month=month, day=day)

	return render_template('day_in_history.html', entries=entries, selected_date=selected_date)

@app.route('/words')
def words():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_YEAR)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date.asc())

	if (end_of_range - start_of_range).days <= 730:
		data_points = WordPresenter(entries).bucket_info(DateStyle.MONTH_YEAR)
	else:
		data_points = WordPresenter(entries).bucket_info(DateStyle.YEAR)

	chart = charts.WordChart()
	chart.labels.labels = list(data_points.keys())
	chart.data.data = list(data_points.values())
	chartJSON = chart.get()
	template_args = {
		'chartJSON': chartJSON
	}

	template_args.update(parser.template_args())

	return render_template('words.html', **template_args)

@app.route('/ngrams')
def ngrams():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_YEAR)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date.asc())

	presenter = NGramPresenter(entries)
	chart_buckets = [presenter.bucket_info(3), presenter.bucket_info(4), presenter.bucket_info(5)]

	chartJSONs = []
	for (index, chart_info) in enumerate(chart_buckets):
		chart = charts.NGramChart()
		chart.labels.labels = list(chart_info.keys())
		chart.data.data = list(chart_info.values())

		chart.options.title = {'text': "Most Common {} word combinations".format(index+3), 'display': True}
		chartJSON = chart.get()
		chartJSONs.append(chartJSON)

	template_args = {
		'charts': chartJSONs
	}

	template_args.update(parser.template_args())

	return render_template('ngrams.html', **template_args)

@app.route('/sentiment')
def sentiment():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_YEAR)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date.asc())

	if (end_of_range - start_of_range).days <= 730:
		data_points = SentimentPresenter(entries).bucket_info(DateStyle.MONTH_YEAR)
	else:
		data_points = SentimentPresenter(entries).bucket_info(DateStyle.YEAR)


	chart = charts.SentimentChart()
	chart.labels.labels = list(data_points.keys())
	chart.data.data = list(data_points.values())
	chartJSON = chart.get()
	template_args = {
		'chartJSON': chartJSON,
		'formAction':'/sentiment',
		'heading': 'Sentiment Over Time',
		'description': 'Average sentiment score for entries in the selected range, grouped by month (or by year for ranges longer than two years).',
		'page': 'range',
	}

	template_args.update(parser.template_args())

	return render_template('sentiment.html', **template_args)

@app.route('/monthly_sentiment')
def sentiment_by_month():
	years = _calculate_years_for_selector()
	year = int(request.args.get('year', '0')) or (years[-1] if years else datetime.now().year)

	start_of_range = datetime(year=year, month=1, day=1)
	end_of_range = datetime(year=year, month=12, day=31)

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date)

	data_points = SentimentPresenter(entries).bucket_info(DateStyle.MONTH)

	labels = [calendar.month_abbr[int(index)] for index in data_points.keys()]

	chart = charts.SentimentByMonthChart()
	chart.labels.labels = labels
	chart.data.data = list(data_points.values())
	chartJSON = chart.get()
	template_args = {
		'chartJSON': chartJSON,
		'formAction':'/monthly_sentiment',
		'heading': 'Sentiment by Month',
		'description': 'Average sentiment score for each calendar month within the selected year, to spot seasonal patterns.',
		'page': 'year',
		'years': years,
		'selected_year': year,
	}

	return render_template('sentiment.html', **template_args)

@app.route('/distribution_sentiment')
def distribution_sentiment():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_ALL)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date)

	data_points = SentimentBucketPresenter(entries).bucket_info()

	chart = charts.SentimentChart()
	chart.labels.labels = list(data_points.keys())
	chart.data.data = list(data_points.values())
	chartJSON = chart.get()
	template_args = {
		'chartJSON': chartJSON,
		'formAction':'/distribution_sentiment',
		'heading': 'Sentiment Distribution',
		'description': 'How many days in the selected range fall into each sentiment score bucket, showing the overall shape (mostly neutral, skewed positive, etc.).',
		'page': 'range',
	}

	template_args.update(parser.template_args())

	return render_template('sentiment.html', **template_args)

@app.route('/analyze_sentiment')
def analyze_sentiment():
	entry_text = request.args.get('entry_text')
	use_internal_classifier = request.args.get('use_internal_classifier')
	internal_classifier = None
	if use_internal_classifier:
		internal_classifier = Classifier.build_local_classifier()

	sentence_breakdown = {}
	sentences = nltk.tokenize.sent_tokenize(entry_text)
	for sentence in sentences:
		if internal_classifier:
			sentence_breakdown[sentence] = internal_classifier.classify(sentence).max
		else:
			sentence_breakdown[sentence] = TextBlob(sentence).sentiment.polarity

	return sentence_breakdown

@app.route('/names')
def names_over_time():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_ALL)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date)

	data_points = NamesPresenter(entries).bucket_info(DateStyle.DAY)

	excluded_names = _load_excluded_names()
	candidate_names = [name for name in data_points if name.lower() not in excluded_names]
	top_names = sorted(
		candidate_names,
		key=lambda name: sum(data_points[name].values()),
		reverse=True)[:MAX_NAME_SERIES]

	labels = sorted(
		{key for name in top_names for key in data_points[name].keys()},
		key=lambda label: datetime.strptime(label, DateStyle.DAY.value))

	chart = charts.NameChart()
	chart.labels.labels = labels
	# Build a fresh data class per request instead of mutating the shared
	# JournalBaseChart.data class, which every chart type inherits from.
	chart.data = type('NamesChartData', (), {})
	for index, name in enumerate(top_names):
		buckets = data_points[name]
		color = NAME_CHART_COLORS[index % len(NAME_CHART_COLORS)]
		series = type(name, (), {
			'label': name,
			'data': [buckets.get(label, 0) for label in labels],
			'borderColor': color,
			'backgroundColor': color,
			'fill': False,
		})
		setattr(chart.data, name, series)

	chartJSON = chart.get()
	template_args = {
		'chartJSON': chartJSON,
		'formAction':'/names'
	}

	template_args.update(parser.template_args())

	return render_template('names.html', **template_args)

@app.route('/names_comparison')
def names_comparison():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_ALL)
	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	exclude_raw = request.args.get('exclude', '')
	excluded_names = _load_excluded_names() | {name.strip().lower() for name in exclude_raw.split(',') if name.strip()}

	top_n = int(request.args.get('top_n', '0')) or DEFAULT_TOP_N
	if top_n not in TOP_N_OPTIONS:
		top_n = DEFAULT_TOP_N

	buckets = _consolidate_into_buckets(start_of_range, end_of_range, MAX_COMPARISON_BUCKETS)
	bucket_labels = [_bucket_label(bucket_start, bucket_end) for bucket_start, bucket_end in buckets]

	# Every name's total in each bucket - not just the top-N - so we can rank by
	# total mentions across the *whole* range afterward instead of per bucket. Ranking
	# per bucket would drop a name that's consistently just outside any single
	# period's top N even though their overall total is high.
	bucket_name_totals = []
	for bucket_start, bucket_end in buckets:
		entries = models.JournalEntry.query.filter(
			and_(models.JournalEntry.entry_date >= bucket_start, models.JournalEntry.entry_date <= bucket_end))

		data_points = NamesPresenter(entries).bucket_info(DateStyle.MONTH_YEAR)
		name_totals = {
			name: sum(counts.values())
			for name, counts in data_points.items()
			if name.lower() not in excluded_names
		}
		bucket_name_totals.append(name_totals)

	overall_totals = {}
	for name_totals in bucket_name_totals:
		for name, count in name_totals.items():
			overall_totals[name] = overall_totals.get(name, 0) + count

	top_names = sorted(overall_totals, key=lambda name: overall_totals[name], reverse=True)[:top_n]

	# Stacked bar chart: one series per name, so each bar is split into the
	# contribution of each of the top names for that time period.
	chart = charts.NameTimelineChart()
	chart.labels.labels = bucket_labels
	chart.data = type('NamesTimelineChartData', (), {})
	for index, name in enumerate(top_names):
		color = NAME_CHART_COLORS[index % len(NAME_CHART_COLORS)]
		series = type(name, (), {
			'label': name,
			'data': [totals.get(name, 0) for totals in bucket_name_totals],
			'borderColor': color,
			'backgroundColor': color,
		})
		setattr(chart.data, name, series)
	chartJSON = chart.get()

	# Heatmap: same names, already sorted by total mentions across the whole range.
	heatmap_max = max(
		(totals.get(name, 0) for totals in bucket_name_totals for name in top_names),
		default=0)
	heatmap_rows = [
		{
			'name': name,
			'cells': [
				{
					'count': totals.get(name, 0),
					'color': _heatmap_color(totals.get(name, 0), heatmap_max),
				}
				for totals in bucket_name_totals
			],
		}
		for name in top_names
	]

	template_args = {
		'chartJSON': chartJSON,
		'exclude_raw': exclude_raw,
		'top_n': top_n,
		'top_n_options': TOP_N_OPTIONS,
		'bucket_labels': bucket_labels,
		'heatmap_rows': heatmap_rows,
	}

	template_args.update(parser.template_args())

	return render_template('names_comparison.html', **template_args)

@app.route('/places')
def places_timeline():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_ALL)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_range,
			models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date)

	gap_days = app.config['TIMELINE_GAP_DAYS']
	timeline = LocationTimelinePresenter(entries, gap_days=gap_days).timeline()

	template_args = {
		'timeline': timeline,
		'formAction':'/places'
	}

	template_args.update(parser.template_args())

	return render_template('places.html', **template_args)

@app.route('/search')
def search():
	name = request.args.get('name', '').strip()
	place = request.args.get('place', '').strip()
	query = request.args.get('query', '').strip()

	filters = []
	if name:
		filters.append(models.JournalEntry.names.any(name))
	if place:
		filters.append(models.JournalEntry.locations.any(place))
	if query:
		filters.append(models.JournalEntry.entry_text.ilike('%{}%'.format(query)))

	entries = []
	if filters:
		entries = models.JournalEntry.query.filter(and_(*filters)) \
			.order_by(models.JournalEntry.entry_date.desc()).all()

	template_args = {
		'entries': entries,
		'has_search': bool(filters),
		'name': name,
		'place': place,
		'query': query,
		'all_names': _distinct_array_values(models.JournalEntry.names),
		'all_places': _distinct_array_values(models.JournalEntry.locations),
	}

	return render_template('search.html', **template_args)

def _parse_month_param(param_name, default):
	try:
		return datetime.strptime(request.args.get(param_name, ''), '%Y-%m')
	except ValueError:
		return default

def _month_bounds(month_start):
	return month_start, month_start + relativedelta(months=+1) - relativedelta(days=+1)

def _load_excluded_names():
	return {excluded_name.name.lower() for excluded_name in models.ExcludedName.query.all()}

def _consolidate_into_buckets(start_of_range, end_of_range, max_buckets):
	"""Split [start_of_range, end_of_range] into consecutive, month-aligned chunks,
	as narrow as possible while keeping the total chunk count at or below max_buckets."""
	start_month = datetime(year=start_of_range.year, month=start_of_range.month, day=1)
	end_month = datetime(year=end_of_range.year, month=end_of_range.month, day=1)
	total_months = (end_month.year - start_month.year) * 12 + (end_month.month - start_month.month) + 1
	chunk_size = max(1, math.ceil(total_months / max_buckets))

	buckets = []
	cursor = start_month
	while cursor <= end_month:
		bucket_end_month = min(cursor + relativedelta(months=+(chunk_size - 1)), end_month)
		bucket_end = bucket_end_month + relativedelta(months=+1) - relativedelta(days=+1)
		buckets.append((cursor, bucket_end))
		cursor = bucket_end_month + relativedelta(months=+1)
	return buckets

def _bucket_label(bucket_start, bucket_end):
	if bucket_start.year == bucket_end.year and bucket_start.month == bucket_end.month:
		return '{} {}'.format(calendar.month_abbr[bucket_start.month], bucket_start.year)
	if bucket_start.year == bucket_end.year:
		return '{}-{} {}'.format(calendar.month_abbr[bucket_start.month], calendar.month_abbr[bucket_end.month], bucket_start.year)
	return '{} {} - {} {}'.format(
		calendar.month_abbr[bucket_start.month], bucket_start.year,
		calendar.month_abbr[bucket_end.month], bucket_end.year)

def _heatmap_color(value, max_value):
	"""Blue at an opacity proportional to value/max_value, so cells are comparable
	at a glance; a small floor keeps zero-mention cells visible instead of blank white."""
	alpha = 0.06 + 0.74 * (value / max_value) if max_value > 0 else 0.06
	return 'rgba(100, 156, 199, {:.2f})'.format(alpha)

def _distinct_array_values(column):
	rows = db.session.query(func.unnest(column).label('value')).distinct().all()
	return sorted({row.value for row in rows if row.value}, key=str.lower)

@app.route('/status')
def entries_status():
	entries = models.JournalEntry.query.order_by(models.JournalEntry.entry_date.desc()).all()
	analyzed_count = sum(1 for entry in entries if entry.word_count is not None)

	return render_template('status.html',
		entries=entries,
		total_count=len(entries),
		analyzed_count=analyzed_count)

def _calculate_years_for_selector():
	first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
	if first_entry is None:
		return []

	years = []
	for year in range(first_entry.entry_date.year, datetime.now().year+1):
		years.append(year)

	return years

@app.route('/import', methods=['GET', 'POST'])
def import_entries():
	global operation_threads

	if request.method == 'GET':
		return render_template('import.html')

	uploaded_file = request.files.get('export_file')
	if not uploaded_file or not uploaded_file.filename:
		logger.warning("Import submitted with no file selected")
		return render_template('analyze.html', error=(
			"Choose a journal export file to import."
		))

	try:
		data = json.load(uploaded_file.stream)
		entries = DailyDiaryJournalEntry.mapFromJSON(data)
	except (json.JSONDecodeError, KeyError, TypeError) as error:
		logger.error("Could not read uploaded file %s: %s", uploaded_file.filename, error)
		return render_template('analyze.html', error=(
			"{} couldn't be read ({}). Check that it's valid JSON in the expected format."
		).format(uploaded_file.filename, error))

	thread_id = random.randint(0, 10000)
	operation_threads[thread_id] = JournalImporter(entries)
	operation_threads[thread_id].run()
	logger.info("Imported %d entries from uploaded file %s", len(entries), uploaded_file.filename)

	return render_template('analyze.html', thread_id=thread_id)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze_entries():
	global operation_threads

	entry_ids_param = request.form.get('entry_ids') if request.method == 'POST' else None

	if entry_ids_param is not None:
		entry_ids = [int(id) for id in entry_ids_param.split(',') if id]
		entries = models.JournalEntry.query.filter(models.JournalEntry.id.in_(entry_ids)).all()
	elif request.args.get('only_unanalyzed'):
		entries = models.JournalEntry.query.filter(models.JournalEntry.word_count.is_(None)).all()
	else:
		entries = models.JournalEntry.query.all()

	thread_id = random.randint(0, 10000)
	operation_threads[thread_id] = JournalEntryAnalyzer(entries)
	operation_threads[thread_id].run()

	return render_template('analyze.html', thread_id=thread_id)

@app.route('/import_photos')
def import_photos():
	global operation_threads

	thread_id = random.randint(0, 10000)
	operation_threads[thread_id] = PhotoImporter()
	operation_threads[thread_id].run()

	return render_template('analyze.html', thread_id=thread_id)

@app.route('/progress-analyze/<int:thread_id>')
def analyze_progress(thread_id):
	global operation_thread

	percent_complete = operation_threads[thread_id].percent_complete
	total_entries = operation_threads[thread_id].total_entries_to_analyze
	return {'percent_complete': percent_complete, 'total_entries': total_entries }

@app.route('/config', methods=['GET', 'POST'])
def config():
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		already_known = models.KnownName.query.filter(func.lower(models.KnownName.name) == name.lower()).first()
		if name and not already_known:
			db.session.add(models.KnownName(name=name))
			db.session.commit()
			logger_config.info("Added known name '%s'", name)
		return redirect(url_for('config'))

	known_names = models.KnownName.query.order_by(models.KnownName.name).all()
	known_locations = models.KnownLocation.query.order_by(models.KnownLocation.location).all()
	excluded_names = models.ExcludedName.query.order_by(models.ExcludedName.name).all()
	return render_template('config.html',
		known_names=known_names, known_locations=known_locations, excluded_names=excluded_names)

@app.route('/config/delete/<int:known_name_id>', methods=['POST'])
def config_delete(known_name_id):
	known_name = models.KnownName.query.get(known_name_id)
	if known_name is not None:
		db.session.delete(known_name)
		db.session.commit()
		logger_config.info("Removed known name '%s'", known_name.name)
	return redirect(url_for('config'))

@app.route('/config/locations', methods=['POST'])
def config_add_location():
	location = request.form.get('location', '').strip()
	already_known = models.KnownLocation.query.filter(func.lower(models.KnownLocation.location) == location.lower()).first()
	if location and not already_known:
		db.session.add(models.KnownLocation(location=location))
		db.session.commit()
		logger_config.info("Added known location '%s'", location)
	return redirect(url_for('config'))

@app.route('/config/locations/delete/<int:known_location_id>', methods=['POST'])
def config_delete_location(known_location_id):
	known_location = models.KnownLocation.query.get(known_location_id)
	if known_location is not None:
		db.session.delete(known_location)
		db.session.commit()
		logger_config.info("Removed known location '%s'", known_location.location)
	return redirect(url_for('config'))

@app.route('/config/excluded_names', methods=['POST'])
def config_add_excluded_name():
	name = request.form.get('excluded_name', '').strip()
	already_excluded = models.ExcludedName.query.filter(func.lower(models.ExcludedName.name) == name.lower()).first()
	if name and not already_excluded:
		db.session.add(models.ExcludedName(name=name))
		db.session.commit()
		logger_config.info("Added excluded name '%s'", name)
	return redirect(url_for('config'))

@app.route('/config/excluded_names/delete/<int:excluded_name_id>', methods=['POST'])
def config_delete_excluded_name(excluded_name_id):
	excluded_name = models.ExcludedName.query.get(excluded_name_id)
	if excluded_name is not None:
		db.session.delete(excluded_name)
		db.session.commit()
		logger_config.info("Removed excluded name '%s'", excluded_name.name)
	return redirect(url_for('config'))