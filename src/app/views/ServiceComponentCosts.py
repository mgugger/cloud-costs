import math
from flask_admin import BaseView, expose
from peewee import JOIN, fn
from src.model import ServiceComponent, Resource, Account
from src.helper.User import current_user_roles

class ServiceComponentCosts(BaseView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    @expose('/')
    def index(self):
        services = ServiceComponent.select(
                ServiceComponent.name,
                Account.provider,
                Account.account_name,
                fn.SUM(Resource.cost).alias('cost')
            ) \
            .join(Resource, JOIN.LEFT_OUTER) \
            .where(Resource.invoice.is_null()) \
            .join(Account, JOIN.LEFT_OUTER) \
            .switch(ServiceComponent) \
            .order_by(Account.provider, ServiceComponent.name) \
            .group_by(ServiceComponent.name) \
            .dicts()

        return self.render('service_components.html', services=services, math=math)