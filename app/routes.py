import calendar
import json
import logging
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
	try:
		start_of_month = datetime.strptime(request.args.get('month', ''), '%Y-%m')
	except ValueError:
		start_of_month = datetime(year=now.year, month=now.month, day=1)

	end_of_month = start_of_month + relativedelta(months=+1) - relativedelta(days=+1)

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

	top_names = sorted(
		data_points.keys(),
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
	return render_template('config.html', known_names=known_names, known_locations=known_locations)

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