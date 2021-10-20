from peewee import TextField, DecimalField, DateTimeField, ForeignKeyField, Model
from src.settings import Settings
from src.model.Invoice import Invoice
from src.model.Account import Account
from src.model.DataImport import DataImport
from src.model.ServiceComponent import ServiceComponent

class Resource(Model):
    service = TextField(index=True)
    category = TextField(index=True)
    region = TextField(null=True, index=True)
    quantity = TextField()
    cost = DecimalField()
    tags = TextField(null=True)
    cost_center = TextField(null=True)
    instance_id = TextField(null=True)
    term = TextField(null=True, index=True)
    date = DateTimeField(null=True)

    account = ForeignKeyField(Account, null=True, default=None, index=True)
    invoice = ForeignKeyField(Invoice, null=True, default=None, index=True)
    service_invoice = ForeignKeyField(Invoice, null=True, default=None, index=True)
    service_component = ForeignKeyField(ServiceComponent, null=True, default=None, index=True)
    data_import = ForeignKeyField(DataImport, null=False, on_delete='CASCADE', index=True)

    class Meta:
        database = Settings().db
        