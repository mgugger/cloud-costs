import math
from flask_admin import BaseView, expose
from flask import request
from src.model import Service, Invoice
from src.helper.User import current_user
from src.constants import Constants

class ServiceDetailView(BaseView):
    def is_accessible(self):
        return current_user() is not None

    @expose('/')
    def index(self):
        service_id = request.args.get('service_id', None)
        invoice_id = request.args.get('invoice_id', None)

        services = Service.select(Service.name, Service.id) \
            .order_by(Service.name) \
            .dicts().execute()
        invoices = Invoice.select(
                Invoice.date,
                Invoice.provider,
                Invoice.id) \
            .where(Invoice.provider == Constants.ManagedCloudServices) \
            .order_by(Invoice.date.desc()).execute()

        results = []
        total_costs = None
        if service_id:
            service = Service.get(Service.id == int(service_id))
            invoice_id = request.args.get('invoice_id', None)

            service_components2service = service.get_servicecomponents2service()
            service_component_ids = \
                [sc2s.service_component.id for sc2s in service_components2service]

            if invoice_id:
                invoice = Invoice.get(Invoice.id == int(invoice_id))
                results = service.get_detailed_costs(invoices=[invoice])
                resource_costs = \
                    service.get_resource_costs(service_component_ids, invoices=[invoice])

            else:
                results = service.get_detailed_costs()
                resource_costs = service.get_resource_costs(service_component_ids)

            total_costs = service.get_costs(service_components2service, resource_costs)

        return self.render('servicedetail.html',
            services=services,
            selected_service_id=service_id,
            selected_invoice_id=invoice_id,
            resource_costs=results,
            total_costs=total_costs,
            math=math,
            str=str,
            invoices=invoices
        )
