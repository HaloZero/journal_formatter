import calendar
import json
import os
import pdb
import nltk
import random

from flask import render_template, flash, redirect, url_for, request
from app import app, db, models
from datetime import datetime
from dateutil.relativedelta import *
from sqlalchemy import and_
from sqlalchemy.sql.expression import func
from textblob import TextBlob

from app.presenters import DateStyle, SentimentPresenter, SentimentBucketPresenter, NGramPresenter, WordPresenter
from app.analyzer import JournalEntryAnalyzer
from app.importer import DailyDiaryJournalEntry, JournalImporter

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
    now = datetime.now()
    start_year = int(request.args.get('start_year', '0')) or now.year-1
    start_month = int(request.args.get('start_month', '0')) or now.month

    end_year = int(request.args.get('end_year', '0')) or now.year
    end_month = int(request.args.get('end_month', '0')) or now.month

    start_of_range = datetime(year=start_year, month=start_month, day=1)
    end_of_range = datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1)
    entries = models.JournalEntry.query.filter(
        and_(models.JournalEntry.entry_date >= start_of_range,
            models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date.asc())

    if (end_of_range - start_of_range).days <= 730:
        data_points = WordPresenter(entries).bucket_info(DateStyle.MONTH_YEAR)
    else: 
        data_points = WordPresenter(entries).bucket_info(DateStyle.YEAR)

    years = _calculate_years_for_selector()

    return render_template('words.html', years=years, start_of_range=start_of_range, 
        end_of_range=end_of_range, labels=data_points.keys(), values=data_points.values())

@app.route('/ngrams')
def ngrams():
    now = datetime.now()
    start_year = int(request.args.get('start_year', '0')) or now.year-1
    start_month = int(request.args.get('start_month', '0')) or now.month

    end_year = int(request.args.get('end_year', '0')) or now.year
    end_month = int(request.args.get('end_month', '0')) or now.month

    start_of_range = datetime(year=start_year, month=start_month, day=1)
    end_of_range = datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1)
    entries = models.JournalEntry.query.filter(
        and_(models.JournalEntry.entry_date >= start_of_range,
            models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date.asc())

    presenter = NGramPresenter(entries)
    graph_labels = [presenter.bucket_info(3), presenter.bucket_info(4), presenter.bucket_info(5)]

    years = _calculate_years_for_selector()

    return render_template('ngrams.html', years=years, start_of_range=start_of_range, 
        end_of_range=end_of_range, graph_labels=graph_labels)

@app.route('/sentiment')
def sentiment():
    now = datetime.now()
    start_year = int(request.args.get('start_year', '0')) or now.year-1
    start_month = int(request.args.get('start_month', '0')) or now.month

    end_year = int(request.args.get('end_year', '0')) or now.year
    end_month = int(request.args.get('end_month', '0')) or now.month

    start_of_range = datetime(year=start_year, month=start_month, day=1)
    end_of_range = datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1)
    entries = models.JournalEntry.query.filter(
        and_(models.JournalEntry.entry_date >= start_of_range,
            models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date.asc())

    if (end_of_range - start_of_range).days <= 730:
        data_points = SentimentPresenter(entries).bucket_info(DateStyle.MONTH_YEAR)
    else:
        data_points = SentimentPresenter(entries).bucket_info(DateStyle.YEAR)

    years = _calculate_years_for_selector()

    chartOptions = {
        'legend': {
            'display': 0
        }
    }

    return render_template('sentiment.html', years=years, start_of_range=start_of_range, 
        end_of_range=end_of_range, labels=data_points.keys(), values=data_points.values(),
        chartOptions=chartOptions, chartType='line',
        formAction='/sentiment')

@app.route('/monthly_sentiment')
def sentiment_by_month():
    start_year = int(request.args.get('start_year', '0'))
    start_month = int(request.args.get('start_month', '0'))

    end_year = int(request.args.get('end_year', '0'))
    end_month = int(request.args.get('end_month', '0'))

    first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
    last_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date.desc()).first()
    
    start_of_range = datetime(year=start_year, month=start_month, day=1) if start_year else first_entry.entry_date
    end_of_range = datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1) if end_year else last_entry.entry_date

    entries = models.JournalEntry.query.filter(
        and_(models.JournalEntry.entry_date >= start_of_range,
            models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date)

    data_points = SentimentPresenter(entries).bucket_info(DateStyle.MONTH)

    years = _calculate_years_for_selector()
    labels = [calendar.month_abbr[int(index)] for index in data_points.keys()]

    chartOptions = {
        'legend': {
            'display': 0
        },
        'scales': {
            'yAxes': [{
                'display': 'true',
                'ticks': {
                    'suggestedMin': 0,
                    'suggestedMax': 0.1,
                }
            }]
        }
    }

    return render_template('sentiment.html', years=years, start_of_range=start_of_range, 
        end_of_range=end_of_range, labels=labels, values=data_points.values(), 
        chartOptions=chartOptions, chartType='bar',
        formAction='/monthly_sentiment')

@app.route('/distribution_sentiment')
def distribution_sentiment():
    start_year = int(request.args.get('start_year', '0'))
    start_month = int(request.args.get('start_month', '0'))

    end_year = int(request.args.get('end_year', '0'))
    end_month = int(request.args.get('end_month', '0'))

    first_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date).first()
    last_entry = models.JournalEntry.query.order_by(models.JournalEntry.entry_date.desc()).first()

    start_of_range = datetime(year=start_year, month=start_month, day=1) if start_year else first_entry.entry_date
    end_of_range = datetime(year=end_year, month=end_month, day=1) + relativedelta(months=+1) - relativedelta(days=+1) if end_year else last_entry.entry_date

    entries = models.JournalEntry.query.filter(
        and_(models.JournalEntry.entry_date >= start_of_range,
            models.JournalEntry.entry_date <= end_of_range)).order_by(models.JournalEntry.entry_date)

    data_points = SentimentBucketPresenter(entries).bucket_info()

    years = _calculate_years_for_selector()

    chartOptions = {
        'legend': {
            'display': 0
        }
    }

    return render_template('sentiment.html', years=years, start_of_range=start_of_range, 
        end_of_range=end_of_range, labels=data_points.keys(), values=data_points.values(), 
        chartOptions=chartOptions, chartType='bar',
        formAction='/distribution_sentiment')

@app.route('/analyze_sentiment')
def analyze_sentiment():
    entry_text = request.args.get('entry_text')
    use_internal_classifier = request.args.get('use_internal_classifier')
    internal_classifier = None
    if use_internal_classifier:
        internal_classifier =Classifier.build_local_classifier()

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