import os
import datetime
import pytest
from src.importer.AzureImport import AzureImport
from src.model import Resource, ServiceCustomer, Service, ServiceComponent, Invoice
from src.invoicing import Invoicer
from src.constants import Constants
from src.invoicing.Mailer import Mailer
from src.tests.helper import assert_import_worked, assert_invoice

TODAY = datetime.date.today()
class TestAzureServiceCustomer(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")
        azImport = AzureImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azure.csv")

        assert_import_worked()

    @pytest.mark.dependency(depends=['TestAzureServiceCustomer::test_import'])
    def test_service_component(self, mocker, db):
        # Assign existing service component to service
        service_component = ServiceComponent.get()
        service_component.relative_price_percentage = 300
        service_component.absolute_price = 100
        service_component.save()
        
        # # Setup ServiceCustomer
        service_customer = ServiceCustomer.create(
             name = 'company1',
             service_description = 'kubernetes-service-qa',
             account_owner_email = os.environ['CCOE_EMAIL'],
             cost_center = '1234500-0000327300',
             sap_service_product_nr = 'SapServiceTBD',
        )
        service = Service.get(name = "TestCustomerService")
        service.service_customer = service_customer
        service.save()

        # Invoice Managed Cloud Services
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)

        # CSV with 1 ServiceCustomer & empty line
        assert len(csv.split('\n')) == 2, "The exported csv is incorrect"
        assert "TestCustomerService" in csv, "The exported csv does not contain the TestCustomerService"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert invoices[0].output is not None, "Invoice output is empty"
        assert invoices[0].amount == 103, "Invoice has incorrect amount"

        # assert existing service_invoice
        query = Resource \
            .select() \
            .where(Resource.service_component.is_null(False)) \
            .execute()
        assert len(query) > 0, "there are resources with service component"
        assert all([x.service_invoice == invoices[0] for x in query]), "All resources with service component should be invoiced"

    @pytest.mark.dependency(depends=['TestAzureServiceCustomer::test_service_component'])
    def test_service_component_not_invoiced_twice(self, mocker, db):
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)

        invoices = Invoice.select().execute()
        assert len(invoices) == 2, "There should still be 2 invoices, one with the resource invoiced and one with the fixed amount"
        assert_invoice(invoices[0], None, 103)
        assert_invoice(invoices[1], csv, 100)

    @pytest.mark.dependency(depends=['TestAzureServiceCustomer::test_service_component'])
    def test_mailer(self, mocker, db):
        mocker.patch('src.invoicing.Email.send', return_value=None)
        emails = Mailer.send_mails_with_last_billing_info()
        assert len(emails) == 1, "one email should have been sent"
        assert len(emails[0].csvs) == 1, "one csv should have been attached"
        assert "TestCustomerService;TestServiceComponent;TestServiceComponent;1;103" in emails[0].csvs[0]

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in (os.environ['CCOE_EMAIL'])

        email_csvs = [email.csvs for email in emails]
        assert "service;servicePart;serviceComponent;quantity;cost_chf;cost_center;date\r\nTestCustomerService;TestServiceComponent;TestServiceComponent;1;103;1234500-0000327300;{0}.{1}\r\n".format(TODAY.year, TODAY.month) in email_csvs[0][0]

    @pytest.mark.dependency(depends=['TestAzureServiceCustomer::test_service_component_not_invoiced_twice'])
    def test_service_component_invoiced_also_without_resource(self, mocker, db):

        Resource.delete().execute()
        Invoice.delete().execute()
        csv = Invoicer.invoice_resources(Constants.ManagedCloudServices)

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be only 1 invoice"
        assert_invoice(invoices[0], csv, 100)

    @pytest.mark.dependency(depends=['TestAzureServiceCustomer::test_service_component_not_invoiced_twice'])
    def test_mailer_not_invoiced_twice(self, mocker, db):
        mocker.patch('src.invoicing.Email.send', return_value=None)
        emails = Mailer.send_mails_with_last_billing_info()
        assert len(emails) == 1, "one email should have been sent"
        assert len(emails[0].csvs) == 1, "one csv should have been attached"
        assert "TestCustomerService;TestServiceComponent;TestServiceComponent;1;100" in emails[0].csvs[0]

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in (os.environ['CCOE_EMAIL'])

        email_csvs = [email.csvs for email in emails]
        assert "service;servicePart;serviceComponent;quantity;cost_chf;cost_center;date\r\nTestCustomerService;TestServiceComponent;TestServiceComponent;1;100;1234500-0000327300;{0}.{1}\r\n".format(TODAY.year, TODAY.month) in email_csvs[0][0]
