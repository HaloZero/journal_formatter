import os
from urllib.parse import urlsplit, urlunsplit

os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5433/journal_python_test')

import psycopg2
from psycopg2 import sql
import pytest


def _ensure_database_exists(database_url):
	parts = urlsplit(database_url)
	dbname = parts.path.lstrip('/')
	admin_url = urlunsplit(parts._replace(path='/postgres'))

	conn = psycopg2.connect(admin_url)
	conn.autocommit = True
	try:
		with conn.cursor() as cursor:
			cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
			if cursor.fetchone() is None:
				cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
	finally:
		conn.close()


_ensure_database_exists(os.environ['DATABASE_URL'])

from app import app as flask_app, db as _db


@pytest.fixture(scope='session', autouse=True)
def app_context():
	ctx = flask_app.app_context()
	ctx.push()
	_db.create_all()
	yield flask_app
	_db.drop_all()
	ctx.pop()


@pytest.fixture(autouse=True)
def clean_db():
	yield
	_db.session.rollback()
	for table in reversed(_db.metadata.sorted_tables):
		_db.session.execute(table.delete())
	_db.session.commit()
