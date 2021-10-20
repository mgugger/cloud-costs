import os
import pytest
from src.importer.AwsImport import AwsImport
from src.model.Resource import Resource
from src.model.Account import Account
from src.model.Invoice import Invoice
from src.invoicing.Invoicer import Invoicer
from src.constants import Constants
from src.model.ServiceCustomer import ServiceCustomer
from src.helper.DatabaseCompressor import DatabaseCompressor


#@pytest.mark.skip(reason="slow test")
class TestAwsCompress(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        awsImport = AwsImport("AwsImport")
        mocker.patch.object(awsImport, 'get_secret', return_value="test mock")
        mocker.patch.object(awsImport, 'get_exchange_rate', side_effect=lambda: 1)
        awsImport.run("sample_files/AWSBilling/20190601-20190701/AWSBilling-00001.csv.zip")

    @pytest.mark.dependency(depends=['TestAwsCompress::test_import'])
    def test_invoice(self, mocker, db):        
        service_customer = ServiceCustomer.create(
            name = 'company1',
            service_description = 'kubernetes-service-qa',
            account_owner_email =  os.environ['CCOE_EMAIL'],
            cost_center = '12345000-000003285',
            sap_service_product_nr = 'SapServiceTBD',
        )
        Account.update(service_customer = service_customer).execute()

        Invoicer.invoice_resources(Constants.AwsProvider)
        old_invoice = Invoice.select().get()

        rows_count = Resource.select().count()
        DatabaseCompressor.compress()
        rows_count_compressed = Resource.select().count()
        assert rows_count > rows_count_compressed, "Compressed Rows should be fewer"
 
        old_invoice_amount = old_invoice.amount
        Resource.update(invoice = None).where(Resource.invoice == old_invoice).execute()
        old_invoice.delete_instance()

        Invoicer.invoice_resources(Constants.AwsProvider)
        new_invoice = Invoice.select().get()
        assert new_invoice.amount == old_invoice_amount, "amounts should be equal"
