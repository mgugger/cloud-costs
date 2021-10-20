import os
import pytest
from src.model import ServiceComponent, ServiceComponentPart, ServiceCustomer, Invoice, Service, ServiceComponent2Service, DataImport, Resource
from src.invoicing import Invoicer
from src.constants import Constants
from src.invoicing.Mailer import Mailer
from src.tests.helper import assert_invoice

class TestServiceComponentPartPercentage(object):
    @pytest.mark.dependency()
    def test_service_component_part_relative_price(self, mocker, db):        
        # Assign existing service component to service
        service_component = ServiceComponent.create(name="k8s_cluster")
        service_component.relative_price_percentage = 100
        service_component.absolute_price = 50
        service_component.save()

        data_import = DataImport.create(data_import_key='test', provider='test')
        Resource.create(service='k8s_resource', category='resource1', cost=100, service_component=service_component, quantity=1, data_import = data_import)

        service_component_part_cpu = ServiceComponentPart.create(name="cpu", service_component_price_percentage=50, service_component=service_component, description="cpu")
        service_component_part_memory = ServiceComponentPart.create(name="ram", service_component_price_percentage=50, service_component=service_component, description="memory")
        service_component_part_storage = ServiceComponentPart.create(name="storage", price_per_unit="5", service_component=service_component, description="storage")

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
            service_component_part = service_component_part_cpu,
            service =  service,
            quantity = 0.3
        )

        sc2sc3 = ServiceComponent2Service.create(
            name = "ns_ram",
            service_component = service_component,
            service_component_part = service_component_part_memory,
            service =  service,
            quantity = 0.4
        )

        sc2sc4 = ServiceComponent2Service.create(
            name = "ns_storage",
            service_component = service_component,
            service_component_part = service_component_part_storage,
            service =  service,
            quantity = 3
        )

        # Invoice Managed Cloud Services
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)
        print(csv)

        # CSV with 3 ServiceCustomer & empty line
        assert len(csv.split('\n')) == 2, "The exported csv is incorrect"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        total_costs = 150 + 23 + 30 + 15
        # Namespace = 50 + (100% * 100) ==> 150 
        # CPU = 50 * 0.5 * 0.3 + (Resource Cost 100 * 0.5 * 0.3) = 7.5 + 15 = rounded 23
        # Memory = 50 * 0.5 * 0.4 * (Resource Cost 100 * 0.5 * 0.4) = 10 + 20 = 30
        # Storage Quantity 3 * Price_per_unit 5 = 15
        assert_invoice(invoices[0], csv, total_costs)

    @pytest.mark.dependency(depends=['TestServiceComponentPartPercentage::test_service_component_part_relative_price'])
    def test_mailer(self, mocker, db):
        mocker.patch('src.invoicing.Email.send', return_value=None)
        emails = Mailer.send_mails_with_last_billing_info()
        assert len(emails) == 1, "one email should have been sent"
        assert len(emails[0].csvs) == 1, "one csv should have been attached"
        assert "MyApp;namespace;k8s_cluster;1;150" in emails[0].csvs[0]
        assert "MyApp;ns_cpu;k8s_cluster;0.3;23" in emails[0].csvs[0]
        assert "MyApp;ns_ram;k8s_cluster;0.4;30" in emails[0].csvs[0]
        assert "MyApp;ns_storage;k8s_cluster;3;15" in emails[0].csvs[0]