from sqlalchemy import Column, String, SmallInteger, Integer, Enum, Boolean, ForeignKey, DateTime
from .core import db

# This has to be in this file to avoid circular dependencies
# Actual logic related to this data is in dayof.py
class SignIn(db.Model):
    id          = Column(Integer,     nullable=False, primary_key=True)
    badge_data  = Column(String(128),  nullable=False, unique=True)
    signed_out  = Column(Boolean, nullable=False, default=False)
    meal_1      = Column(SmallInteger, nullable=False, default=0)
    meal_2      = Column(SmallInteger, nullable=False, default=0)
    meal_3      = Column(SmallInteger, nullable=False, default=0)
    meal_4      = Column(SmallInteger, nullable=False, default=0)
    meal_5      = Column(SmallInteger, nullable=False, default=0)
    meal_7      = Column(SmallInteger, nullable=False, default=0)
    meal_8      = Column(SmallInteger, nullable=False, default=0)
    meal_9      = Column(SmallInteger, nullable=False, default=0)
