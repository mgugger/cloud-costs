from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import BasePeeweeFilter
from peewee import JOIN
from src.model.Service import Service
from src.model.Account import Account
from src.model.Resource import Resource
from src.model.ServiceComponent import ServiceComponent
from src.model.ServiceComponent2Service import ServiceComponent2Service
from src.helper.User import current_user_roles

class FilterHasServiceAttached(BasePeeweeFilter):
    def apply(self, query, value):
        if value == '1':
            return query.join(ServiceComponent2Service).distinct()
        else:
            return query.join(ServiceComponent2Service, JOIN.LEFT_OUTER) \
                .where(ServiceComponent2Service.id.is_null())

    def operation(self):
        return 'Has Service'

class FilterByService(BasePeeweeFilter):
    def apply(self, query, value):
        return query.join(ServiceComponent2Service) \
            .where(ServiceComponent2Service.service_id == value) \
            .distinct()

    def operation(self):
        return 'Service'

class FilterByAccount(BasePeeweeFilter):
    def apply(self, query, value):
        return query \
            .join(Resource) \
            .join(Account) \
            .where(Account.id == value) \
            .distinct()

    def operation(self):
        return 'Account'

class ServiceComponentView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    def get_services():
        return [(x.id, x.name) for x in Service.select().execute()]

    def get_accounts():
        return [(x.id, x.account_name) for x in Account.select().execute()]


    column_filters = [
        FilterHasServiceAttached(
            ServiceComponent.name, 'Has Service', options=(('1', 'Yes'), ('0', 'No'))
        ),
        FilterByService(ServiceComponent.name, 'Service', options=get_services),
        FilterByAccount(ServiceComponent.name, 'Account', options=get_accounts)
    ]

    edit_modal = True
    create_modal = True
    column_list = ('name', 'description', 'absolute_price', 'relative_price_percentage',
        'fixed_service_price' ,'sla_info', 'service_component_parts', 'account')
    column_searchable_list = ['name']
    column_editable_list = ('absolute_price', 'relative_price_percentage', 'fixed_service_price')