import math
from src.model import Resource, Account,ServiceCustomer,Service,ServiceComponent2Service

def assert_import_worked(check_import_service=True, check_import_service_customer=True):
    assert (Resource.select().count()) > 0, "Import did not import any resources"
    assert (Account.select().count()) > 0, "Import did not import any accounts"
    if check_import_service_customer:
        assert (ServiceCustomer.select().count()) > 0, "Import did not create service customers"

    if check_import_service:
        assert (Service.select().count()) > 0, "did not import the customerservice tag"
        assert (ServiceComponent2Service.select().count()) > 0, "did not create service component 2 service connections"

def assert_invoice(invoice, export_csv, invoice_amount):
    assert invoice.output is not None, "Invoice output is empty"
    assert invoice.amount == invoice_amount, "Invoice has incorrect amount"
    if export_csv:
        exported_amount = math.fsum([float(csvline.split(';')[4]) for csvline in export_csv.split('\n')[:-1]])
        assert invoice.amount == exported_amount, "Invoiced Amount should match with amount in exported csv"