import math

from flask_admin import BaseView, expose
from flask import request
from peewee import fn
from src.helper.User import current_user_roles
from src.model import Account, Service, ServiceCustomer, Resource

class NetProfitView(BaseView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    @expose('/')
    def index(self):
        cloud_integration_accounts = Account \
            .select(Account.account_name, Account.provider, fn.SUM(Resource.cost).alias('amount')) \
            .join(Resource) \
            .where(Resource.invoice.is_null()) \
            .where(
                Account.account_name.startswith('company2-subscription-')
                | Account.account_name.startswith('company2-gke-')
            ) \
            .group_by(Account.account_name) \
            .order_by(fn.SUM(Resource.cost).desc()) \
            .dicts()

        service_earnings = 0
        services = Service.select() \
            .join(ServiceCustomer) \
            .execute()
        for service in services:
            service_components2service = service.get_servicecomponents2service()
            service_component_ids = \
                [sc2s.service_component.id for sc2s in service_components2service]
            resource_costs = service.get_resource_costs(service_component_ids)
            # sum costs
            service_earnings += service.get_costs(service_components2service, resource_costs)

        return self.render('netprofit_view.html',
            cloud_integration_accounts=cloud_integration_accounts,
            service_earnings=math.ceil(service_earnings),
            request_headers=request.headers,
            math=math
        )
