from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterEmpty,FilterInList
from flask_admin.contrib.peewee.filters import BasePeeweeFilter
from peewee import JOIN
from src.model.Service import Service
from src.model.ServiceCustomer import ServiceCustomer
from src.helper.User import current_user_roles

class FilterHasInvalidCostCenter(BasePeeweeFilter):
    def apply(self, query, value):
        if value == '1':
            print(value)
            return query.where(not ServiceCustomer.cost_center.regexp(r"(\d{7}-\d{10}$)"))
        else:
            print(value)
            return query.where(ServiceCustomer.cost_center.regexp(r"\d{7}-\d{10}$"))

    def operation(self):
        return 'Has Invalid CostCenter'

class FilterHasNoService(BasePeeweeFilter):
    def apply(self, query, value):
        if value == '1':
            print(value)
            return query.join(Service, JOIN.LEFT_OUTER).where(Service.id.is_null())
        else:
            print(value)
            return query.join(Service, JOIN.LEFT_OUTER).where(Service.id.is_null(False))

    def operation(self):
        return 'Has No service attached'

class ServiceCustomerView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    column_filters = [
        FilterHasInvalidCostCenter(
            ServiceCustomer.name, 'Has Invalid CostCenter', options=(('1', 'Yes'), ('0', 'No'))
        ),
        FilterHasNoService(
            ServiceCustomer.name, 'Has No service attached', options=(('1', 'Yes'), ('0', 'No'))
        ),
    ]
    column_searchable_list = ['cost_center', 'name', 'account_owner_email']

    edit_modal = True
    create_modal = True
    can_export = True
