import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(BASE_DIR, 'data')


class Config:
	SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://localhost:5433/journal_python'
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	SPACY_MODEL = os.environ.get('SPACY_MODEL', 'en_core_web_trf')
	TIMELINE_GAP_DAYS = int(os.environ.get('TIMELINE_GAP_DAYS', '14'))
	PHOTO_SOURCE_DIR = os.environ.get('PHOTO_SOURCE_DIR') or os.path.join(DATA_DIR, 'photos')
	MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # cap uploads (journal export via /import) at 20MB
