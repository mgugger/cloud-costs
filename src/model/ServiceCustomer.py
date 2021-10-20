from peewee import Model, TextField

from src.settings import Settings

class ServiceCustomer(Model):
    name = TextField()
    account_owner_email = TextField(null=True, index=True)
    cost_center = TextField(null=True, index=True)

    def __str__(self):
        return f"{self.name} / {self.cost_center}"

    def get_friendly_name(self):
        return f"{self.name} {self.account_owner_email} {self.cost_center}"


    class Meta:
        database = Settings().db
