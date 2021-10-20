from peewee import Model, TextField
from src.settings import Settings

class ServiceType(Model):
    name = TextField()

    def __str__(self):
        return str(self.name)

    class Meta:
        database = Settings().db
