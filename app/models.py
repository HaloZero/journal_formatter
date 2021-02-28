from nltk.tokenize import word_tokenize
from textblob import TextBlob
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import db
import string 

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_text = db.Column(db.String)
    timestamp = db.Column(db.Integer)
    entry_date = db.Column(db.Date, index=True)
    names = db.Column(db.ARRAY(db.String))
    word_count = db.Column(db.Integer)
    sentence_count = db.Column(db.Integer)
    paragraph_count = db.Column(db.Integer)

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