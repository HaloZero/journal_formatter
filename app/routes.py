import calendar
import json
import os
import pdb
import nltk
import random

from flask import render_template, flash, redirect, url_for, request
from app import app, db, models, charts
from datetime import datetime
from dateutil.relativedelta import *
from sqlalchemy import and_
from sqlalchemy.sql.expression import func
from textblob import TextBlob

from app.classifier import Classifier
from app.presenters import DateStyle, SentimentPresenter, SentimentBucketPresenter, NGramPresenter, WordPresenter
from app.analyzer import JournalEntryAnalyzer
from app.importer import DailyDiaryJournalEntry, JournalImporter
from app.parsers import DateRangeParser, RequestLengthStyle

APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'static')

operation_threads = {}

class SelectedDate:
	def __init__(self, year=None, month=None, day=None):
		self.year = year
		self.month = month
		self.day = day

@app.route('/')
def index():
	now = datetime.now()
	year = int(request.args.get('year', '0')) or now.year
	month = int(request.args.get('month', '0')) or now.month

	start_of_month = datetime(year=year, month=month, day=1)
	end_of_month = start_of_month + relativedelta(months=+1) - relativedelta(days=+1)

	entries = models.JournalEntry.query.filter(
		and_(models.JournalEntry.entry_date >= start_of_month,
			models.JournalEntry.entry_date <= end_of_month))

	years = _calculate_years_for_selector()
	selected_date = SelectedDate(year=year, month=month)

	return render_template('index.html', entries=entries, years=years, selected_date=selected_date)

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
	month = int(request.args.get('month', '0')) or now.month
	day = int(request.args.get('day', '0')) or now.day

	first_year = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first().entry_date.year
	valid_dates = []
	for year in range(first_year, datetime.now().year+1):
		valid_dates.append(datetime(year=year, month=month, day=day))

	entries = models.JournalEntry.query.filter(models.JournalEntry.entry_date.in_(valid_dates))
	years = _calculate_years_for_selector()
	selected_date = SelectedDate(year=year, month=month, day=day)

	return render_template('day_in_history.html', entries=entries, years=years, selected_date=selected_date)

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
		'formAction':'/sentiment'
	}

	template_args.update(parser.template_args())

	return render_template('sentiment.html', **template_args)

@app.route('/monthly_sentiment')
def sentiment_by_month():
	parser = DateRangeParser(request, RequestLengthStyle.DEFAULT_ALL)

	start_of_range = parser.start_of_range()
	end_of_range = parser.end_of_range()

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
		'formAction':'/monthly_sentiment'
	}

	template_args.update(parser.template_args())

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
		'formAction':'/distribution_sentiment'
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

def _calculate_years_for_selector():
	first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
	years = []
	for year in range(first_entry.entry_date.year, datetime.now().year+1):
		years.append(year)

	return years

@app.route('/import')
def import_entries():
	global operation_threads

	thread_id = random.randint(0, 10000)

	filepath = os.path.join(APP_STATIC, 'diary-downloaded.json')
	with open(filepath) as f:
		data = json.load(f)
		entries = DailyDiaryJournalEntry.mapFromJSON(data)
		operation_threads[thread_id] = JournalImporter(entries)
		operation_threads[thread_id].run()

	return render_template('analyze.html', thread_id=thread_id)

@app.route('/analyze')
def analyze_entries():
	global operation_threads
	entries = models.JournalEntry.query.all()

	thread_id = random.randint(0, 10000)
	operation_threads[thread_id] = JournalEntryAnalyzer(entries)
	operation_threads[thread_id].start()

	return render_template('analyze.html', thread_id=thread_id)

@app.route('/progress-analyze/<int:thread_id>')
def analyze_progress(thread_id):
	global operation_thread

	percent_complete = operation_threads[thread_id].percent_complete
	total_entries = operation_threads[thread_id].total_entries_to_analyze
	return {'percent_complete': percent_complete, 'total_entries': total_entries }