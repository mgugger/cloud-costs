import os
import pytest
from src.importer.AzureImport import AzureImport
from src.model import ServiceCustomer,AdditionalInvoicePosition,Account,Invoice
from src.invoicing import Invoicer
from src.constants import Constants
from src.tests.helper import assert_invoice

class TestMultipleAdditionalInvoicePositionPositive(object):
    @pytest.mark.dependency()
    def test_account_discount(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")

        az_import = AzureImport("AzureImport")
        mocker.patch.object(az_import, 'get_secret', return_value="test mock")
        az_import.run("sample_files/azure.csv")

        service_customer1 = ServiceCustomer.create(
            name = 'Customer2',
            service_description = 'kubernetes-service-qa',
            account_owner_email = os.environ['CCOE_EMAIL'],
            cost_center = '1234500-0000327300',
            sap_service_product_nr = 'SapServiceTBD'
        )

        service_customer2 = ServiceCustomer.create(
            name = 'Customer2',
            service_description = 'resource1',
            account_owner_email = 'CloudCenterofExcellence2@company2.ch',
            cost_center = '1234500-0000251182',
            sap_service_product_nr = 'SapServiceTBD'
        )

        discount1 = AdditionalInvoicePosition.create(
            reason = "Test Discount",
            amount = -20,
            provider = Constants.AzureProvider,
            service_customer = service_customer1,
            invoice = None
        )
        
        discount2 = AdditionalInvoicePosition.create(
            reason = "Test Add",
            amount = 30,
            provider = Constants.AzureProvider,
            service_customer = service_customer1,
            invoice = None
        )

        discount3 = AdditionalInvoicePosition.create(
            reason = "Test Add",
            amount = 40,
            provider = Constants.AzureProvider,
            service_customer = service_customer1,
            invoice = None
        )

        total_discount = discount1.amount + discount2.amount + discount3.amount

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

        assert all([x.invoice == invoices[0] for x in AdditionalInvoicePosition.select().execute()])

        csv = Invoicer.invoice_resources(Constants.AzureProvider)
        assert len(csv.split('\n')) == 1, "No Resources to be invoiced"