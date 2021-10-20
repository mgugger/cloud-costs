from peewee import Model, TextField, DecimalField, CharField, ForeignKeyField
from src.settings import Settings
from src.model.ServiceCustomer import ServiceCustomer
from src.model.Invoice import Invoice

class AdditionalInvoicePosition(Model):
    reason = TextField()
    amount = DecimalField()
    provider = CharField(index=True)
    service_customer = ForeignKeyField(ServiceCustomer, index=True)
    invoice = ForeignKeyField(Invoice, index=True, null=True, default=None)

    class Meta:
        database = Settings().db
