from flask_admin.contrib.peewee import ModelView
from flask_admin.contrib.peewee.filters import FilterInList
from src.model import ServiceComponent2Service, Service, ServiceComponent
from flask_admin.contrib.peewee.filters import BasePeeweeFilter
from peewee import JOIN
from src.helper.User import current_user_roles

class FilterHasServiceAttached(BasePeeweeFilter):
    def apply(self, query, value):
        if value == '1':
            return query.join(Service).distinct()
        else:
            return query.join(Service, JOIN.LEFT_OUTER).where(Service.id.is_null())

    def operation(self):
        return 'Has Service'

class ServiceComponent2ServiceView(ModelView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    def get_services():
        return [(x.id, x.name) for x in Service.select().execute()]

    def get_service_component():
        return [(x.id, x.name) for x in ServiceComponent.select().execute()]

    column_filters = [
        FilterHasServiceAttached(
            ServiceComponent2Service.name, 'Has Service', options=(('1', 'Yes'), ('0', 'No'))
        ),
        FilterInList(ServiceComponent2Service.service, 'Service', options=get_services),
        FilterInList(
            ServiceComponent2Service.service_component,
            'Service Component',
            options=get_service_component
        )
    ]

    edit_modal = True
    create_modal = True
    can_export = True

    column_searchable_list = ['name']

    column_editable_list = ('service', 'quantity')

