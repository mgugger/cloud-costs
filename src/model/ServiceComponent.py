from peewee import TextField, IntegerField, Model

from src.settings import Settings

class ServiceComponent(Model):
    name = TextField()
    description = TextField(null=True)
    absolute_price = IntegerField(null=True, default=None)
    relative_price_percentage = IntegerField(null=True, default=None)
    fixed_service_price = IntegerField(null=True, default=None)
    sla_info = TextField(null=True)

    def __str__(self):
        return str(self.name)

    @property
    def account(self):
        from src.model import Account, Resource
        accounts = Account \
            .select(Account.account_name, Account.provider) \
            .join(Resource) \
            .where(Resource.service_component_id == self.id) \
            .distinct() \
            .execute()
        return list(accounts)

    @property
    def service_component_parts(self):
        # Local Import to avoid circular imports
        from src.model import ServiceComponentPart
        parts = ServiceComponentPart \
            .select() \
            .where(ServiceComponentPart.service_component == self) \
            .execute()
        return ''.join([f"{part.name}/{part.price_per_unit}" for part in parts])

    class Meta:
        database = Settings().db
