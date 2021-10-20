from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterInList
from src.model import Account, ServiceCustomer
from src.helper.User import current_user_roles

class AccountViewReadOnly(ModelView):
    def is_accessible(self):
        return "admin" not in current_user_roles()

    def get_providers():
        providers = Account.select(Account.provider).distinct().execute()
        return [(x.provider,x.provider) for x in providers]

    def get_service_customers():
        return [(x.id, x.name) for x in ServiceCustomer.select().distinct().execute()]

    column_filters = [
        FilterInList(Account.provider, 'Provider', options=get_providers),
        FilterInList(Account.service_customer, 'Service Customer', options=get_service_customers)
    ]

    column_searchable_list = ['account_name']
    column_exclude_list = ('percentage_charge', 'account_id', 'sap_service_product_nr')

    can_export = True
    can_create = False
    can_edit = False
    can_delete = False
