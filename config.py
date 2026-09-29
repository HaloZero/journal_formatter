import os


class Config:
	SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql:///journal_python'
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	SPACY_MODEL = os.environ.get('SPACY_MODEL', 'en_core_web_lg')
	TIMELINE_GAP_DAYS = int(os.environ.get('TIMELINE_GAP_DAYS', '14'))
