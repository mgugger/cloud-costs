import os
import pytest
from src.importer.AwsImport import AwsImport
from src.importer.AzureImport import AzureImport
from src.model import Account, Invoice
from src.invoicing import Invoicer, Mailer
from src.constants import Constants
from src.model.ServiceCustomer import ServiceCustomer
from src.tests.helper import assert_import_worked, assert_invoice

#@pytest.mark.skip(reason="slow test")
class TestMultipleProviderImport(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        awsImport = AwsImport("AwsImport")
        mocker.patch.object(awsImport, 'get_secret', return_value="test mock")
        mocker.patch.object(awsImport, 'get_exchange_rate', side_effect=lambda: 1)
        awsImport.run("sample_files/AWSBilling/20190601-20190701/AWSBilling-00001.csv.zip")

        azImport = AzureImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azure.csv")

        assert_import_worked()

    @pytest.mark.dependency(depends=['TestMultipleProviderImport::test_import'])
    def test_invoice(self, mocker, db):
        service_customer = ServiceCustomer.create(
            name = 'company3 IT-Dev',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD',
        )
        Account.update(service_customer = service_customer).execute()

        csv = Invoicer.invoice_resources(Constants.AzureProvider)
        print(csv)
        invoices = Invoice.select().execute()
        print(invoices[0].output)
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert_invoice(invoices[0], csv, 7)
        
        csv = Invoicer.invoice_resources(Constants.AwsProvider)

        invoices = Invoice.select().execute()
        assert len(invoices) == 2, "There should be 1 existing invoice"
        assert_invoice(invoices[1], csv, 700)

    @pytest.mark.dependency(depends=['TestMultipleProviderImport::test_invoice'])
    def test_mailer(self, mocker, db):
        mocker.patch('src.invoicing.Mailer.send_email')
        emails = Mailer.send_mails_with_last_billing_info()
        email_bodies = [email.body for email in emails]
        for email_body in email_bodies:
            print(email_body)
        assert any("[AWS] AWS: CHF 700" in body for body in email_bodies)

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in (os.environ['CCOE_EMAIL'])
            
        assert len(Mailer.send_email.call_args_list) == 1, "1 email should have been sent"
    
  