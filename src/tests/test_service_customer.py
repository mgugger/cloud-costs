import os
import math
import pytest
from src.model import ServiceComponent,ServiceCustomer,Service,ServiceComponent2Service,Resource,Invoice,DataImport
from src.invoicing import Invoicer,Mailer
from src.constants import Constants
from src.tests.helper import assert_invoice

class TestServiceCustomer(object):
    @pytest.mark.dependency()
    def test_service_component(self, mocker, db):        
        # Assign existing service component to service
        service_component = ServiceComponent.create(name="service1component")
        service_component.relative_price_percentage = 77
        service_component.absolute_price = 100
        service_component.save()

        # Service Customer 1
        # Setup ServiceCustomer
        service_customer1 = ServiceCustomer.create(
            name = 'company1',
            service_description = 'kubernetes-service-qa',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD'
        )

        service = Service.create(name="TestService", service_customer=service_customer1)

        # Create Sample Service Component Quantity
        sc2sc1 = ServiceComponent2Service.create(
            name = "company2-xy-qa",
            service_component = service_component,
            service =  service,
            quantity = 1
        )

        data_import = DataImport.create(data_import_key='test', provider='test')
        Resource.create(service='resource1', category='resource1', cost=100, service_component=service_component, quantity=1, data_import = data_import)

        # Assign existing service component to service
        service_component2 = ServiceComponent.create(name="service2component")
        service_component2.relative_price_percentage = 50
        service_component2.absolute_price = 20
        service_component2.save()   

        service2_customer1 = ServiceCustomer.create(
            name = 'company1',
            service_description = 'kubernetes2-service-qa',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD'
        )
         # Service 2
        service2 = Service.create(name="TestService2", service_customer=service2_customer1)

        sc2sc1 = ServiceComponent2Service.create(
            name = "company2-documatrix-prod",
            service_component = service_component2,
            service =  service2,
            quantity = 2
        )

        service2_customer2 = ServiceCustomer.create(
            name = 'Industry1',
            service_description = 'kubernetes2-service-qa',
            account_owner_email = 'test12354@company2.ch',
            cost_center = '1234500-0000021000',
            sap_service_product_nr = 'SapServiceTBD'
        )
        service3 = Service.create(name="TestService3", service_customer=service2_customer2)

        sc2sc1 = ServiceComponent2Service.create(
            name = "company2-application1-dev",
            service_component = service_component2,
            service =  service3,
            quantity = 2,
            delete_after_invoice = True
        )

        # Invoice Managed Cloud Services
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)
        print(csv)

        # CSV with 3 ServiceCustomer & empty line
        assert len(csv.split('\n')) == 4, "The exported csv is incorrect"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert_invoice(invoices[0], csv, 257)

        # assert existing service_invoice
        query = Resource \
            .select() \
            .where(Resource.service_component.is_null(False)) \
            .execute()
        assert all([x.service_invoice is not None for x in query]), "All resources with service component should be invoiced"

    @pytest.mark.dependency(depends=['TestServiceCustomer::test_service_component'])
    def test_mailer(self, mocker, db):
        mocker.patch('src.invoicing.Mailer.send_email')
        emails = Mailer.send_mails_with_last_billing_info()
        email_bodies = [email.body for email in emails]
  
        assert any("TestService: CHF 177" in body for body in email_bodies)
        assert any("TestService2: CHF 40" in body for body in email_bodies)
        assert any("TestService3: CHF 40" in body for body in email_bodies)

        # Mailer deletes sc2s that should only be invoiced once
        assert not ServiceComponent2Service.select().where(ServiceComponent2Service.name == "company2-application1-dev").exists(), "the service component should be deleted after invoice"

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in ("test123@company2.ch", os.environ['CCOE_EMAIL'], "test1234@company2.ch")

        email_csvs = [email.csvs for email in emails]
        assert "TestService;company2-xy-qa;service1component;1;177" in email_csvs[0][0]
        assert "TestService2;company2-documatrix-prod;service2component;2;40" in email_csvs[1][0]
        assert "TestService3;company2-application1-dev;service2component;2;40" in email_csvs[2][0]
            
        assert len(Mailer.send_email.call_args_list) == 3, "3 emails should have been sent"

    @pytest.mark.dependency(depends=['TestServiceCustomer::test_service_component'])
    def test_service_component_invoiced_also_without_resource(self, mocker, db):
        Resource.delete().execute()
        Invoice.delete().execute()
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be only 1 invoice"
        assert invoices[0].amount == 140, "Invoice has incorrect amount"
        assert invoices[0].amount == math.fsum([float(csvline.split(';')[4]) for csvline in csv.split('\n')[:-1]]), "Invoiced Amount should match with amount in exported csv"

