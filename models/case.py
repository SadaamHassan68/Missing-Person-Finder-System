from datetime import datetime
from database import db

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Open')
    description = db.Column(db.Text)
    guardian_phone = db.Column(db.String(20), nullable=False)
    last_seen_location = db.Column(db.String(100))
    last_seen_address = db.Column(db.Text)
    last_seen_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    person = db.relationship('Person', backref='cases')
    user = db.relationship('User', backref='cases')

    def save(self):
        if not self.id:
            db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'person': self.person.to_dict(),
            'status': self.status,
            'description': self.description,
            'guardian_phone': self.guardian_phone,
            'last_seen_location': self.last_seen_location,
            'last_seen_address': self.last_seen_address,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 