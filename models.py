from app import db

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_text = db.Column(db.String)
    timestamp_key = db.column(db.Integer)
    entry_date = db.Column(db.Date, index=True)
    names = db.Column(db.Array(String))
    word_count = db.Column(db.Integer)
    sentence_count = db.Column(db.Integer)
    paragraph_count = db.Column(db.Integer)

    def __repr__(self):
        return '<Journal entry for {}>'.format(self.entry_date)    
