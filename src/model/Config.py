from peewee import Model, CharField
from src.settings import Settings

class Config(Model):
    key = CharField(index=True)
    value = CharField(index=False)

    class Meta:
        database = Settings().db
