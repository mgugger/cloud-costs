from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterInList
from src.helper.User import current_user_roles
from src.model import ServiceComponent, ServiceComponentPart

class ServiceComponentPartView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    def get_service_component():
        return [(x.id, x.name) for x in ServiceComponent.select().execute()]

    column_filters = [
        FilterInList(
            ServiceComponentPart.service_component,
            'Service Component',
            options=get_service_component
        )
    ]
    column_searchable_list = ['name', 'description']
