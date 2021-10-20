from peewee import Model, TextField, CharField, ForeignKeyField, DecimalField
from src.settings import Settings
from src.model import ServiceCustomer

class Account(Model):
    account_name = TextField(null=True, index=True)
    account_id = CharField(unique=True)
    provider = CharField(index=True)
    service_customer = ForeignKeyField(ServiceCustomer, null=True, default=None, index=True)
    sap_service_product_nr = TextField(null=True)
    percentage_charge = DecimalField(default=1)

    def __str__(self):
        return f"{self.account_name} ({self.provider})"

    class Meta:
        database = Settings().db
