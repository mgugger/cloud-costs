from peewee import Model, TextField, ForeignKeyField, BooleanField, DecimalField

from src.settings import Settings
from src.model import ServiceComponent, Service, ServiceComponentPart

class ServiceComponent2Service(Model):
    name = TextField()
    service_component = ForeignKeyField(ServiceComponent, null=False, index=True)
    service_component_part = ForeignKeyField(ServiceComponentPart, null=True, index=False)
    service = ForeignKeyField(Service, null=True, index=True)
    quantity = DecimalField(max_digits=10, decimal_places=5)
    delete_after_invoice = BooleanField(default=False, index=True)

    def __str__(self):
        return f"{self.name}/{self.service.name}/{self.service_component.name}"

    class Meta:
        database = Settings().db
