from peewee import Model, TextField, ForeignKeyField, DecimalField, IntegerField

from src.settings import Settings
from src.model import ServiceComponent

class ServiceComponentPart(Model):
    name = TextField()
    description = TextField(null=True)
    service_component = ForeignKeyField(ServiceComponent, null=False, index=True)
    price_per_unit = DecimalField(null=True)
    service_component_price_percentage = IntegerField(null=True)

    def __str__(self):
        return f"{self.service_component.name}/{self.name}"

    class Meta:
        database = Settings().db
