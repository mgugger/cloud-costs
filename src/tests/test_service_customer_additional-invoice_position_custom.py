import pytest
from src.importer.AzureImport import AzureImport
from src.model import ServiceCustomer,AdditionalInvoicePosition,Account,Invoice, Resource, DataImport
from src.invoicing import Invoicer
from src.constants import Constants
from src.tests.helper import assert_invoice

class TestMultipleAdditionalInvoicePositionCustom(object):
    @pytest.mark.dependency()
    def test_account_discount(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")

        service_customer1 = ServiceCustomer.create(
            name = 'Customer1',
            account_owner_email = 'cloud@company2.ch',
            cost_center = '1234500-0000327300'
        )

        data_import = DataImport.create(
            provider = "Azure",
            data_import_key = "MyDataImportKey"
        )

        accounts = []
        for i in range(1,8):
            account = Account.create(
                account_name = "Account{0}".format(i),
                account_id = "Account{0}".format(i),
                provider = "Azure",
                service_customer = service_customer1
            )
            accounts.append(account)

        # Total: 108452
        costs = [35573, 6822, 5379, 4518, 56158, 2528, 2]
        costs_stack = costs.copy()
        accounts_stack = accounts.copy()
        for account in accounts:
            Resource.create(
                service="ServiceX",
                category="CategoryY",
                region="RegionZ",
                quantity=1,
                cost = costs_stack.pop(),
                account = accounts_stack.pop(),
                data_import = data_import
            )


        discount1 = AdditionalInvoicePosition.create(
            reason = "DiscountX",
            amount = -37529,
            provider = Constants.AzureProvider,
            service_customer = service_customer1,
            invoice = None
        )
        
        discount2 = AdditionalInvoicePosition.create(
            reason = "DiscountY",
            amount = -50,
            provider = Constants.AzureProvider,
            service_customer = service_customer1,
            invoice = None
        )

        csv = Invoicer.invoice_resources(Constants.AzureProvider)

        invoices = Invoice.select().where(Invoice.provider == Constants.AzureProvider).execute()
        assert len(invoices) == 1, "One Azure invoice should exist"
        invoice_amount = sum(costs) + discount1.amount + discount2.amount
        assert_invoice(invoices[0], csv, invoice_amount)
