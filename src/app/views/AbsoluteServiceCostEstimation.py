import math
import os
from flask_admin import BaseView, expose
from src.model import Service, ServiceCustomer
from src.helper.User import current_user_roles

class AbsoluteServiceCostEstimation(BaseView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    @expose('/')
    def index(self):
        result = []
        services = Service.select() \
            .join(ServiceCustomer) \
            .execute()
        for service in services:
            service_components2service = service.get_servicecomponents2service()
            service_component_ids = \
                [sc2s.service_component.id for sc2s in service_components2service]
            resource_costs = service.get_resource_costs(service_component_ids)
            # sum costs
            amount = service.get_costs(service_components2service, resource_costs)

            result.append({
                'ServiceCustomer' : service.service_customer.name,
                'Service' : service.name,
                'Amount' : amount,
                'ServiceId': service.id
            })

        result.sort(key=lambda x: x['Service'])

        return self.render('services.html', services=result, math=math, os=os)
