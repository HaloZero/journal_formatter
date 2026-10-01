from collections import Counter
from datetime import datetime
from nltk.tokenize import word_tokenize
from textblob import TextBlob
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import db
import string

class JournalEntry(db.Model):
    # daily_score is a 1-5 scale filled in by /import_scores - shown on each entry as
    # a face instead of the raw number
    DAILY_SCORE_FACES = {
        1: ('\U0001F623', 'Worst day'),
        2: ('\U0001F641', 'Bad day'),
        3: ('\U0001F610', 'Average day'),
        4: ('\U0001F642', 'Good day'),
        5: ('\U0001F604', 'Best day'),
    }

    id = db.Column(db.Integer, primary_key=True)
    entry_text = db.Column(db.String)
    timestamp = db.Column(db.Integer)
    entry_date = db.Column(db.Date, index=True)
    names = db.Column(db.ARRAY(db.String))
    locations = db.Column(db.ARRAY(db.String))
    word_count = db.Column(db.Integer)
    sentence_count = db.Column(db.Integer)
    paragraph_count = db.Column(db.Integer)
    daily_score = db.Column(db.Integer)
    analyzed_at = db.Column(db.DateTime)
    photos = db.relationship('JournalPhoto', backref='journal_entry', order_by='JournalPhoto.created_at')

    def __repr__(self):
        return '<Journal entry for {}>'.format(self.entry_date)

    def unique_word_count(self):
        entry_text = self.entry_text
        words = word_tokenize(str.lower(entry_text))
        word_set = set(filter(lambda x: x not in string.punctuation, words))
        return len(word_set)

    def sentiment(self):
        return TextBlob(self.entry_text).sentiment

    def sentiment_polarity_formatted(self):
        return round(self.sentiment().polarity, 3)

    def sentiment_polarity_class(self):
        polarity = self.sentiment().polarity
        if polarity > 0.1:
            return 'sentiment-positive'
        elif polarity < -0.1:
            return 'sentiment-negative'
        else:
            return 'sentiment-neutral'

    def daily_score_face(self):
        """(emoji, label) for this entry's 1-5 daily_score, or None if it hasn't been scored."""
        return self.DAILY_SCORE_FACES.get(self.daily_score)

    def unique_names(self):
        return self._value_counts(self.names)

    def unique_locations(self):
        return self._value_counts(self.locations)

    @staticmethod
    def _value_counts(values):
        if not values:
            return []
        counts = Counter(values)
        seen = set()
        ordered = []
        for value in values:
            if value not in seen:
                seen.add(value)
                ordered.append((value, counts[value]))
        return ordered

    @staticmethod
    def stop_words():
        stop_words = stopwords.words('english')
        #Exclude puntuation
        punc = string.punctuation
        for thing in punc:
            stop_words.append(thing)
        stop_words.append('’')
        stop_words.append('”')
        stop_words.append('“')

        return stop_words

class SentimentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.String)
    sentiment = db.Column(db.String)

    def __repr__(self):
        return '<{} sentiment for sentence "{}">'.format(self.sentiment, self.sentence)

class KnownName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)

    def __repr__(self):
        return '<KnownName {}>'.format(self.name)

class KnownLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String, unique=True, nullable=False)

    def __repr__(self):
        return '<KnownLocation {}>'.format(self.location)

class ExcludedName(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)

    def __repr__(self):
        return '<ExcludedName {}>'.format(self.name)

class NameAlias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String, unique=True, nullable=False)
    canonical_name = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<NameAlias {} -> {}>'.format(self.alias, self.canonical_name)

class LocationAlias(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String, unique=True, nullable=False)
    canonical_location = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<LocationAlias {} -> {}>'.format(self.alias, self.canonical_location)

class JournalPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entry.id'), index=True, nullable=False)
    file_path = db.Column(db.String, nullable=False)
    caption = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Photo {} for entry {}>'.format(self.file_path, self.journal_entry_id)