import os
import math
import pytest
from peewee import fn
from src.importer.AzureMarketPlaceImport import AzureMarketPlaceImport
from src.model import Resource, Account, DataImport, Invoice
from src.invoicing import Invoicer, Mailer
from src.constants import Constants
from src.model.ServiceCustomer import ServiceCustomer
from src.tests.helper import assert_import_worked, assert_invoice

class TestAzureMarketPlaceImport(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")
        azImport = AzureMarketPlaceImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azureMarketPlace.json")

        assert_import_worked(check_import_service=False, check_import_service_customer=False)
    
    @pytest.mark.dependency(depends=["TestAzureMarketPlaceImport::test_import"])
    def test_calculate_total_costs(self, db):
        results = {
            'company1 PlayGround Subscription' : 4,
            'company2-32528-DevOps-NET': 0
        }

        res = Resource.select(fn.SUM(Resource.cost).alias('cost'), Account.account_name).join(Account).group_by(Account.account_name).dicts()
        assert len(res) > 0, "No resources have been found in result"
        for row in res:
            assert math.ceil(row['cost']) == results[row['account_name']], "Costs did not match"

    @pytest.mark.dependency(depends=["TestAzureMarketPlaceImport::test_import"])
    def test_data_import_exists(self, db):
        
        res = DataImport.select().execute()
        assert len(res) == 1, "No DataImport found"
        assert res[0].start_time is not None, "DataImport has not started"
        assert res[0].end_time is not None, "DataImport is not finished"

    @pytest.mark.dependency(depends=['TestAzureMarketPlaceImport::test_import'])
    def test_invoice(self, mocker, db):
        service_customer = ServiceCustomer.create(
            name = 'company1',
            service_description = 'kubernetes-service-qa',
            account_owner_email =  os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD',
        )
        Account.update(service_customer = service_customer).execute()

        csv = Invoicer.invoice_resources(Constants.AzureProvider)
        
        # CSV with 2 reserved instances & empty line
        assert len(csv.split('\n')) == 2, "No Resources to be invoiced"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert_invoice(invoices[0], csv, 4)
    
    @pytest.mark.dependency(depends=['TestAzureMarketPlaceImport::test_invoice'])
    def test_mailer(self, mocker, db):
        mocker.patch('src.invoicing.Mailer.send_email')
        emails = Mailer.send_mails_with_last_billing_info()
        email_bodies = [email.body for email in emails]
        for email_body in email_bodies:
            print(email_body)
        assert any("company1 PlayGround Subscription: CHF 4" in body for body in email_bodies)

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in ( os.environ['CCOE_EMAIL'])
            
        assert len(Mailer.send_email.call_args_list) == 1, "1 email should have been sent"