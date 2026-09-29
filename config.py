import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(BASE_DIR, 'data')


class Config:
	SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://localhost:5433/journal_python'
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	SPACY_MODEL = os.environ.get('SPACY_MODEL', 'en_core_web_lg')
	TIMELINE_GAP_DAYS = int(os.environ.get('TIMELINE_GAP_DAYS', '14'))
	PHOTO_SOURCE_DIR = os.environ.get('PHOTO_SOURCE_DIR') or os.path.join(DATA_DIR, 'photos')
