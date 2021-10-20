from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterEmpty,FilterInList
from src.model import Account, ServiceCustomer
from src.helper.User import current_user_roles

class AccountView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    def get_providers():
        accounts = Account.select(Account.provider).distinct().execute()
        return [(x.provider,x.provider) for x in accounts]

    def get_service_customers():
        service_customers = ServiceCustomer \
            .select() \
            .distinct() \
            .order_by(ServiceCustomer.name) \
            .execute()
        return [(x.id, x.name) for x in service_customers]

    column_filters = [
        FilterEmpty(Account.service_customer, 'Has Service Customer'),
        FilterInList(Account.provider, 'Provider', options=get_providers),
        FilterInList(Account.service_customer, 'Service Customer', options=get_service_customers)
    ]

    column_searchable_list = ['account_name']
    column_editable_list = ['percentage_charge', 'service_customer']

    edit_modal = True
    create_modal = True
    can_export = True
