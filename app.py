from flask import Flask
from models import JournalEntry
app = Flask(__name__)

@app.route('/')
def hello_world():
    JournalEntry.query.all()
    return 'Hello, World!'