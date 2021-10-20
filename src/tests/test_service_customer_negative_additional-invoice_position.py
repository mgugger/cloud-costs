import os
import pytest
from src.importer.AzureImport import AzureImport
from src.model import ServiceCustomer,ServiceComponent2Service,DataImport,Service,AdditionalInvoicePosition,Resource,Account,Invoice,ServiceComponent
from src.invoicing import Invoicer,Mailer
from src.constants import Constants
from src.tests.helper import assert_invoice

class TestNegativeAdditionalInvoicePosition(object):
    @pytest.mark.dependency()
    def test_account_discount(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")

        az_import = AzureImport("AzureImport")
        mocker.patch.object(az_import, 'get_secret', return_value="test mock")
        az_import.run("sample_files/azure.csv")

        service_customer1 = ServiceCustomer.create(
            name = 'company1',
            service_description = 'kubernetes-service-qa',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD'
        )

        discount1 = AdditionalInvoicePosition.create(
            reason = "Test Discount",
            amount = -2,
            provider = Constants.AzureProvider,
            service_customer = service_customer1,
            invoice = None
        )

        service_customer2 = ServiceCustomer.create(
            name = 'asdsa resource1',
            service_description = 'resource1',
            account_owner_email = 'CloudCenterofExcellence2@company2.ch',
            cost_center = '1234500-0000251182',
            sap_service_product_nr = '33297'
        )
        
        discount2 = AdditionalInvoicePosition.create(
            reason = "Test Discount",
            amount = -1,
            provider = Constants.AzureProvider,
            service_customer = service_customer2,
            invoice = None
        )

        total_discount = discount1.amount + discount2.amount

        # company3 Dev
        it_company7 = Account.select().where(Account.account_name == "company3 IT-DEV").get()
        it_company7.service_customer = service_customer1
        it_company7.save()

        # le shop
        company4_bi_int = Account.select().where(Account.account_name == "company4-bi-int").get()
        company4_bi_int.service_customer = service_customer2
        company4_bi_int.save()

        csv = Invoicer.invoice_resources(Constants.AzureProvider)

        invoices = Invoice.select().where(Invoice.provider == Constants.AzureProvider).execute()
        assert len(invoices) == 1, "One Azure invoice should exist"
        assert_invoice(invoices[0], csv, 7 + total_discount)

    @pytest.mark.dependency()
    def test_service_discount(self):        
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
        AdditionalInvoicePosition.create(
            reason = "Test Discount",
            amount = -30,
            provider = Constants.ManagedCloudServices,
            service_customer = service_customer1
        )

        service = Service.create(name="TestService", service_customer=service_customer1)

        # Create Sample Service Component Quantity
        ServiceComponent2Service.create(
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

        # Invoice Managed Cloud Services
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)
        print(csv)

        # CSV with 3 ServiceCustomer & empty line
        assert len(csv.split('\n')) == 2, "The exported csv is incorrect"

        invoices = Invoice.select().where(Invoice.provider == Constants.ManagedCloudServices).execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert_invoice(invoices[0], csv, 147)

        # assert existing service_invoice
        query = Resource \
            .select() \
            .where(Resource.service_component.is_null(False)) \
            .execute()
        assert all([x.service_invoice is not None for x in query]), "All resources with service component should be invoiced"
    
    @pytest.mark.dependency(depends=['TestNegativeAdditionalInvoicePosition::test_service_discount'])
    def test_mailer(self, mocker):
        mocker.patch('src.invoicing.Mailer.send_email')
        emails = Mailer.send_mails_with_last_billing_info()
        email_bodies = [email.body for email in emails]
        for email_body in email_bodies:
            print(email_body)
        assert any("Test Discount: CHF -30" in body for body in email_bodies)

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in (os.environ['CCOE_EMAIL'])
            
        assert len(Mailer.send_email.call_args_list) == 3, "3 email should have been sent"