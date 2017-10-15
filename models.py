import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.schema import PrimaryKeyConstraint

db = SQLAlchemy()


class BaseModel(db.Model):
    """Base data model for all objects"""
    __abstract__ = True

    def __init__(self, *args):
        super().__init__(*args)

    def __repr__(self):
        """Define a base way to print models"""
        return '%s(%s)' % (self.__class__.__name__, {
            column: value
            for column, value in self._to_dict().items()
        })

    def json(self):
        """
                Define a base way to jsonify models, dealing with datetime objects
        """
        return {
            column: value if not isinstance(value, datetime.date) else value.strftime('%Y-%m-%d')
            for column, value in self._to_dict().items()
        }


class Estate(BaseModel, db.Model):
    """Model for the estate table"""
    __tablename__ = 'estate'

    title = db.Column(db.TEXT)
    type = db.Column(db.TEXT)
    edited = db.Column(db.DATE)
    price = db.Column(db.NUMERIC)
    real_price = db.Column(db.NUMERIC)
    price_m2 = db.Column(db.NUMERIC)
    price_m2_floors = db.Column(db.NUMERIC)
    price_notes = db.Column(db.TEXT)
    locality = db.Column(db.TEXT)
    state = db.Column(db.TEXT)
    ownership = db.Column(db.TEXT)
    link = db.Column(db.TEXT)
    floor = db.Column(db.SMALLINT)
    floor_string = db.Column(db.TEXT)
    m2 = db.Column(db.NUMERIC)
    m2_floors = db.Column(db.NUMERIC)
    m2_balcony = db.Column(db.NUMERIC)
    m2_cellar = db.Column(db.NUMERIC)
    garage = db.Column(db.BOOLEAN)
    final_inspection_year = db.Column(db.INTEGER)
    energy_rating = db.Column(db.CHAR)
    elevator = db.Column(db.BOOLEAN)
    description = db.Column(db.TEXT)
    seller = db.Column(db.TEXT)
    phone = db.Column(db.TEXT)
    email = db.Column(db.TEXT)
    attractive_offer = db.Column(db.BOOLEAN)
    api_link = db.Column(db.TEXT)
    img_links = db.Column(db.ARRAY(db.TEXT))
    json = db.Column(db.JSON)
    location = db.Column(db.TEXT)
    latitude = db.Column(db.NUMERIC)
    longitude = db.Column(db.NUMERIC)
    id = db.Column(db.TEXT)
    source = db.Column(db.TEXT)
    timestamp = db.Column(db.TIMESTAMP)
    updated = db.Column(db.TIMESTAMP)

    __table_args__ = (
        PrimaryKeyConstraint('id', 'source'),
    )