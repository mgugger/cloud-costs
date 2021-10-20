from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterInList
from src.model import Service, ServiceCustomer
from src.helper.User import current_user_roles

class ServiceViewReadOnly(ModelView):
    def is_accessible(self):
        return "admin" not in current_user_roles()

    def get_service_customers():
        return [(x.id, x.name) for x in ServiceCustomer.select().distinct().execute()]

    column_filters = [
        FilterInList(Service.service_customer, 'Service Customer', options=get_service_customers)
    ]
    column_searchable_list = ['name']
    column_exclude_list = ('description', 'sap_service_product_nr')

    can_export = True
    can_create = False
    can_edit = False
    can_delete = False
