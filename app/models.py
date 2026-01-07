"""Database models for storing prediction history."""
# models.py
# Database models for storing prediction history

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class CropPrediction(db.Model):
    """Model for storing crop recommendation predictions"""
    __tablename__ = 'crop_predictions'

    id = db.Column(db.Integer, primary_key=True)
    user_session = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    nitrogen = db.Column(db.Integer)
    phosphorus = db.Column(db.Integer)
    potassium = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    ph = db.Column(db.Float)
    rainfall = db.Column(db.Float)
    city = db.Column(db.String(100))
    predicted_crop = db.Column(db.String(100))

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_session': self.user_session,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'nitrogen': self.nitrogen,
            'phosphorus': self.phosphorus,
            'potassium': self.potassium,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'ph': self.ph,
            'rainfall': self.rainfall,
            'city': self.city,
            'predicted_crop': self.predicted_crop
        }


class FertilizerPrediction(db.Model):
    """Model for storing fertilizer recommendation predictions"""
    __tablename__ = 'fertilizer_predictions'

    id = db.Column(db.Integer, primary_key=True)
    user_session = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    crop_name = db.Column(db.String(100))
    nitrogen = db.Column(db.Integer)
    phosphorus = db.Column(db.Integer)
    potassium = db.Column(db.Integer)
    recommendation_key = db.Column(db.String(50))

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_session': self.user_session,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'crop_name': self.crop_name,
            'nitrogen': self.nitrogen,
            'phosphorus': self.phosphorus,
            'potassium': self.potassium,
            'recommendation_key': self.recommendation_key
        }


class DiseasePrediction(db.Model):
    """Model for storing disease detection predictions"""
    __tablename__ = 'disease_predictions'

    id = db.Column(db.Integer, primary_key=True)
    user_session = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    image_filename = db.Column(db.String(200))
    predicted_disease = db.Column(db.String(200))
    confidence = db.Column(db.Float)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_session': self.user_session,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'image_filename': self.image_filename,
            'predicted_disease': self.predicted_disease,
            'confidence': self.confidence
        }
