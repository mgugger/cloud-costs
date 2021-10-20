import os
import math
import pytest
from peewee import fn
from src.importer.AzureReservedInstanceImport import AzureReservedInstanceImport
from src.importer.AzureImport import AzureImport
from src.model.Resource import Resource
from src.model.Account import Account
from src.invoicing.Invoicer import Invoicer
from src.constants import Constants
from src.model.ServiceCustomer import ServiceCustomer
from src.tests.helper import assert_import_worked

class TestAzureInvoiceOnlyOnce(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")
        azImport = AzureReservedInstanceImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azureReservedInstance.json")

        azImport = AzureImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azure.csv")

        assert_import_worked()

    @pytest.mark.dependency(depends=["TestAzureInvoiceOnlyOnce::test_import"])
    def test_calculate_total_costs(self, db):
        results = {
            'company1 DevOps Subscription' : 13180,
            'company1 PROD Subscription' : 7924,
            'company3 IT-DEV' : 2,
            'company4-bi-int' : 2,
            'company4-global-acc' : 1,
            'company2-sandbox-dev' : 1,
            'company2-portal' : 1
        }

        res = Resource.select(fn.SUM(Resource.cost).alias('cost'), Account.account_name).join(Account).group_by(Account.account_name).dicts()
        assert len(res) > 0, "No resources have been found in result"
        for row in res:
            assert math.ceil(row['cost']) == results[row['account_name']], "Costs for did not match"

    @pytest.mark.dependency(depends=['TestAzureInvoiceOnlyOnce::test_import'])
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
        print(csv)
        assert len(csv.split('\n')) == 8, ""
        for line in csv.split('\n'):
            if line:
                assert '00-000' in line or '1234567-0000325200' in line, 'csv line does not contain correct cost_center'

        csv = Invoicer.invoice_resources(Constants.AzureProvider)
        assert len(csv.split('\n')) == 1, "No Resources to be invoiced"

        # CSV with 2 reserved instances & empty line
