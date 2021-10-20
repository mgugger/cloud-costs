import os
import math
import pytest
from peewee import fn
from unittest.mock import patch
from src.importer.AwsImport import AwsImport
from src.model import Resource, DataImport, Account, Invoice
from src.invoicing import Invoicer, Mailer
from src.constants import Constants
from forex_python.converter import CurrencyRates
from src.model.ServiceCustomer import ServiceCustomer
from src.tests.helper import assert_import_worked, assert_invoice

#@pytest.mark.skip(reason="slow test")
class TestAwsImport(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        awsImport = AwsImport("AwsImport")
        mocker.patch.object(awsImport, 'get_secret', return_value="test mock")
        mocker.patch.object(awsImport, 'get_exchange_rate', side_effect=lambda: 1)
        awsImport.run("sample_files/AWSBilling/20190601-20190701/AWSBilling-00001.csv.zip")

        assert_import_worked(check_import_service=False, check_import_service_customer=False)

    @pytest.mark.dependency(depends=["TestAwsImport::test_import"])
    def test_calculate_total_costs(self, db):
        results = {
            'AWS' : 700,
        }

        res = Resource.select(fn.SUM(Resource.cost).alias('cost'), Account.account_name).join(Account).group_by(Account.account_name).dicts()
        assert len(res) > 0, "No resources have been found in result"
        for row in res:
            assert math.fabs(math.ceil(row['cost']) - results[row['account_name']]) < 10, "Costs for {} did not match".format(row['account_name'])

    @pytest.mark.dependency(depends=["TestAwsImport::test_import"])
    def test_no_reserved_instances(self, db):
        res = Resource.select().dicts()
        assert len(res) > 0, "No resources have been found in result"
        for row in res:
            assert row['term'] is None

    @pytest.mark.dependency(depends=["TestAwsImport::test_import"])
    def test_data_import_exists(self, db):
        
        res = DataImport.select().execute()
        assert len(res) == 1, "No DataImport found"
        assert res[0].start_time is not None, "DataImport has not started"
        assert res[0].end_time is not None, "DataImport is not finished"

    @pytest.mark.dependency(depends=['TestAwsImport::test_import'])
    def test_invoice(self, mocker, db):        
        service_customer = ServiceCustomer.create(
            name = 'company1',
            service_description = 'kubernetes-service-qa',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD',
        )
        Account.update(service_customer = service_customer).execute()

        csv = Invoicer.invoice_resources(Constants.AwsProvider)

        # CSV with 7 Accounts entries & empty line
        assert len(csv.split('\n')) == 2, "The exported csv is incorrect"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert_invoice(invoices[0], csv, 700)


    @pytest.mark.dependency(depends=['TestAwsImport::test_invoice'])
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