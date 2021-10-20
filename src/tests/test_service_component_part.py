import os
import pytest
from src.model import ServiceComponent, ServiceComponentPart, ServiceCustomer, Invoice, Service, ServiceComponent2Service
from src.invoicing import Invoicer
from src.constants import Constants
from src.tests.helper import assert_invoice

class TestServiceComponentPart(object):
    @pytest.mark.dependency()
    def test_service_component_part(self, mocker, db):        
        # Assign existing service component to service
        service_component = ServiceComponent.create(name="k8s_cluster")
        service_component.relative_price_percentage = 0
        service_component.absolute_price = 50
        service_component.save()

        service_component_part = ServiceComponentPart.create(
            name="cpu",
            price_per_unit="4",
            service_component=service_component,
            description="description"
        )

        # Service Customer 1
        # Setup ServiceCustomer
        service_customer1 = ServiceCustomer.create(
            name = 'Team1',
            service_description = 'kubernetes-service',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD'
        )

        service = Service.create(name="MyApp", service_customer=service_customer1)

        # Create Sample Service Component Quantity
        sc2sc1 = ServiceComponent2Service.create(
            name = "namespace",
            service_component = service_component,
            service =  service,
            quantity = 1
        )

        sc2sc2 = ServiceComponent2Service.create(
            name = "ns_cpu",
            service_component = service_component,
            service_component_part = service_component_part,
            service =  service,
            quantity = 0.5
        )

        # Invoice Managed Cloud Services
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)
        print(csv)

        # CSV with 3 ServiceCustomer & empty line
        assert len(csv.split('\n')) == 2, "The exported csv is incorrect"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        total_costs = 50 + (0.5*4)
        
        assert_invoice(invoices[0], csv, total_costs)
            