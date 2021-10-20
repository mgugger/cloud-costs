from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterEmpty, FilterInList
from src.model import Service, ServiceCustomer
from src.helper.User import current_user_roles

class ServiceView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    def get_service_customers():
        service_customers = ServiceCustomer \
            .select() \
            .distinct() \
            .order_by(ServiceCustomer.name) \
            .execute()
        return [(x.id, x.name) for x in service_customers]

    column_filters = [
        FilterEmpty(Service.service_customer, 'Has Service Customer'),
        FilterEmpty(Service.sap_service_product_nr, 'Has Helpline Service Identifier'),
        FilterInList(
            Service.service_customer, 
            'Service Customer', 
            options=get_service_customers
        )
    ]
    column_searchable_list = ('name', 'description')
    column_exclude_list = ('description', 'id')
    column_editable_list = ['service_type', 'service_customer', 'sap_service_product_nr']

    edit_modal = True
    create_modal = True
    can_export = True
