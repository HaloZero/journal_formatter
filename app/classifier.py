from sqlalchemy import and_, or_ 
from sqlalchemy.sql.expression import func
from app import app, db, models
from textblob.classifiers import NaiveBayesClassifier

class Classifier():
	@staticmethod
	def build_local_classifier():
		training_data = models.SentimentRecord.query.filter(
			or_(models.SentimentRecord.sentiment == "pos", models.SentimentRecord.sentiment == "neg"))
		Classifier.build_classifier(training_data)
		
	@staticmethod
	def build_classifier(training_data):
		training_tuples = Classifier.build_tuples(training_data)
		cl = NaiveBayesClassifier(training_tuples)
		return cl

	@staticmethod
	def build_tuples(training_data):
		training_tuples = []
		for data in training_data:
			training_tuples.append((data.sentence, data.sentiment))
		return training_tuples

	@staticmethod
	def test_local_classifier():
		training_data = models.SentimentRecord.query.filter(or_(models.SentimentRecord.sentiment == "pos", models.SentimentRecord.sentiment == "neg")).order_by(func.random()).all()

		marker = int(len(training_data) * 0.8)
		classifier = Classifier.build_classifier(training_data[:marker])
		test_tuples = Classifier.build_tuples(training_data[marker:])
		return classifier.accuracy(test_tuples)