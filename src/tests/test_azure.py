import os
import math
import pytest
from peewee import fn
from src.importer.AzureImport import AzureImport
from src.model import Resource, Account,ServiceCustomer,DataImport,ServiceComponent,Invoice
from src.invoicing import Invoicer,Mailer
from src.constants import Constants
from src.tests.helper import assert_import_worked, assert_invoice

class TestAzureImport(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")
        azImport = AzureImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azure.csv")

        assert_import_worked()
        
    @pytest.mark.dependency(depends=['TestAzureImport::test_import'])
    def test_overriden_cost_center_tag(self):
        assert (Resource.select().where(Resource.cost_center == "1234500-0000005610").count()) == 4, "There should be 1 custom CostCenterTag in 4 Resources"

    @pytest.mark.dependency(depends=["TestAzureImport::test_import"])
    def test_calculate_total_costs(self):
        results = {
            'company3 IT-DEV' : 2,
            'company4-bi-int' : 2,
            'company4-global-acc' : 1,
            'company2-sandbox-dev' : 1,
            'company2-portal' : 1
        }

        res = Resource.select(fn.SUM(Resource.cost).alias('cost'), Account.account_name).join(Account).group_by(Account.account_name).dicts()
        assert len(res) > 0, "No resources have been found in result"
        for row in res:
            assert math.ceil(row['cost']) == results[row['account_name']], "Costs for {} did not match".format(row['account_name'])

    @pytest.mark.dependency(depends=["TestAzureImport::test_import"])
    def test_data_import_exists(self):
        
        res = DataImport.select().execute()
        assert len(res) == 1, "No DataImport found"
        assert res[0].start_time is not None, "DataImport has not started"
        assert res[0].end_time is not None, "DataImport is not finished"

    @pytest.mark.dependency(depends=["TestAzureImport::test_import"])
    def test_service_component_exists(self):
        
        res = ServiceComponent.select().execute()
        assert len(res) == 1, "No ServiceComponent found"
        assert res[0].name == 'TestServiceComponent', "No Service Component was created from the tag"

    @pytest.mark.dependency(depends=['TestAzureImport::test_import'])
    def test_invoice(self):
        service_customers = {
            os.environ['CCOE_EMAIL']: ['company2-sandbox-dev'],
            'info@company4.ch': ['company4-bi-int', 'company4-global-acc'],
            'company3 it@sowhat.com' : ['company3 IT-DEV'],
            'azuredevops@company1.com' : ['company2-portal'],
            'ShouldNotBeInvoicedBecauseOfZeroValue' : ['company6-newsletterpicturestorage-prod']
        }
        for key in service_customers:
            service_customer = ServiceCustomer.create(
                name = key,
                service_description = 'Test',
                account_owner_email = key,
                cost_center = '1234500-0000327300',
                sap_service_product_nr = 'SapServiceTBD',
            )
            Account.update(service_customer = service_customer).where(Account.account_name.in_(service_customers[key])).execute()

        csv = Invoicer.invoice_resources(Constants.AzureProvider)

        assert '1234500-0000005610' in csv, "The exported CSV does not contain the special costcentertag"

        # CSV with 6 Accounts entries & empty line
        assert len(csv.split('\n')) == 6, "The exported csv is incorrect"

        invoices = Invoice.select().execute()
        assert len(invoices) == 1, "There should be 1 existing invoice"
        assert_invoice(invoices[0], csv, 7)

    @pytest.mark.dependency(depends=['TestAzureImport::test_invoice'])
    def test_mailer(self, mocker):
        mocker.patch('src.invoicing.Mailer.send_email')
        emails = Mailer.send_mails_with_last_billing_info()
        email_bodies = [email.body for email in emails]
        assert any("company3 IT-DEV: CHF 2" in body for body in email_bodies)
        assert any("company4-global-acc: CHF 1" in body for body in email_bodies)
        assert any("company2-sandbox-dev: CHF 1" in body for body in email_bodies)
        assert any("company2-portal: CHF 1" in body for body in email_bodies)

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            assert email_to in (os.environ['CCOE_EMAIL'], "info@company4.ch", "company3 it@sowhat.com", "azuredevops@company1.com")
            
        assert len(Mailer.send_email.call_args_list) == 4, "Four emails should have been sent"

    @pytest.mark.dependency(depends=['TestAzureImport::test_invoice'])
    def test_mailer_single_customer(self, mocker):
        specific_service_customers = list(ServiceCustomer.select().where(ServiceCustomer.name == os.environ['CCOE_EMAIL']))
        invoices = [Invoice.select().first()]

        mocker.patch('src.invoicing.Mailer.send_email')
        emails = Mailer.send_mails_with_last_billing_info(specific_service_customers, invoices)
        email_bodies = [email.body for email in emails]

        email_tos = [email.msg['To'] for email in emails]
        for email_to in email_tos:
            print(email_to)
            assert email_to == os.environ['CCOE_EMAIL']
            
        assert len(Mailer.send_email.call_args_list) == 1, "One email should have been sent"

    @pytest.mark.dependency(depends=["TestAzureImport::test_invoice"])
    def test_delete_import_no_resources_left(self): 
        DataImport.delete().execute()
        assert DataImport.select().count() == 0, "There should be no dataimport left"
        assert Resource.select().count() == 0, "There should be no resources left"
