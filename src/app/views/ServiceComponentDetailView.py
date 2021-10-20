import math
from flask_admin import BaseView, expose
from flask import request
from src.model import ServiceComponent, Resource, ServiceComponent2Service, Service, ServiceComponentPart
from peewee import fn, JOIN, prefetch
import itertools
from src.helper.User import current_user_roles

class ServiceComponentDetailView(BaseView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    @expose('/')
    def index(self):
        service_component_id = request.args.get('service_component_id', None)

        service_components = ServiceComponent \
            .select(ServiceComponent.name, ServiceComponent.id) \
            .dicts() \
            .execute()

        results = []
        total_costs = None
        if service_component_id:
            service_components2service = ServiceComponent2Service.select(
                    ServiceComponent2Service.id,
                    ServiceComponent2Service.name,
                    ServiceComponent2Service.quantity,
                    ServiceComponent2Service.service_component_part_id,
                    ServiceComponent.id,
                    ServiceComponent.name,
                    ServiceComponent.relative_price_percentage,
                    ServiceComponent.fixed_service_price,
                    ServiceComponent.absolute_price,
                    Service.id,
                    Service.name
                ) \
                .join(Service) \
                .switch(ServiceComponent2Service) \
                .join(ServiceComponent) \
                .where(ServiceComponent.id == service_component_id) \
                .order_by(Service.id)
            service_component_parts = ServiceComponentPart.select()
            prefetch(service_components2service, service_component_parts)
            sc2svc_by_group = itertools.groupby(service_components2service, lambda x: x.service)
            for service, service_components2service in sc2svc_by_group:
                results += service.get_detailed_costs(
                    invoices = [],
                    service_components2service = list(service_components2service)
                )

            # sum costs
            total_costs = ServiceComponent.select(fn.SUM(Resource.cost).alias('cost')) \
                .where(ServiceComponent.id == int(service_component_id)) \
                .join(Resource, JOIN.LEFT_OUTER) \
                .where(Resource.invoice.is_null()) \
                .dicts()[0]['cost']

        earnings = math.fsum([result['TotalPrice'] for result in results])

        return self.render('servicecomponentdetail.html',
            service_components=service_components,
            selected_service_component_id=service_component_id,
            resource_costs=results,
            total_costs=total_costs if total_costs else 0,
            math=math,
            str=str,
            earnings=earnings if earnings else 0
        )
