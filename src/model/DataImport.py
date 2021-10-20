import datetime

from peewee import Model, DateTimeField, CharField
from src.settings import Settings

class DataImport(Model):
    start_time = DateTimeField(default=datetime.datetime.now)
    end_time = DateTimeField(default=None, null=True)
    provider = CharField(index=True)
    data_import_key = CharField(unique=True, null=False) # to avoid duplicate importing

    def __str__(self):
        return f"{self.provider} {self.end_time}"

    class Meta:
        database = Settings().db
