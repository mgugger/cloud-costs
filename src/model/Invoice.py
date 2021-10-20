import datetime
from dateutil.relativedelta import relativedelta
from peewee import Model, DateTimeField, IntegerField, DecimalField, CharField, TextField
from src.settings import Settings

class Invoice(Model):
    date = DateTimeField(default=datetime.datetime.now)
    amount = IntegerField()
    usage = DecimalField(max_digits=12)
    provider = CharField(index=True)
    output = TextField(null=True, default=None)

    def get_friendly_name(self):
        return f"{(self.date - relativedelta(months=1)).strftime('%Y.%m')} {self.provider}"

    class Meta:
        database = Settings().db
