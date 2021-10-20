from itertools import groupby
import io
import copy
import csv
import os
import math
from decimal import Decimal
import datetime
from calendar import monthrange

import requests

from peewee import fn

from src.model import ServiceCustomer, Service, Resource, Invoice, AdditionalInvoicePosition, Account
from src.invoicing.CsvExport import CsvExport
from src.invoicing.Email import Email

from src.constants import Constants
from src.helper.Secrets import get_secret

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH_FIRSTDAY = (FIRSTDAY - datetime.timedelta(days=1)).replace(day=1)
LASTMONTH_LASTDAY = LASTMONTH_FIRSTDAY \
    .replace(day=monthrange(LASTMONTH_FIRSTDAY.year, LASTMONTH_FIRSTDAY.month)[1])

class Invoicer(object):
    def invoice_resources(provider):
        if Constants.ManagedCloudServices == provider:
            return Invoicer.invoice_services(provider)
        else:
            return Invoicer.invoice_accounts(provider)

    def invoice_services(provider):
        print(f"Invoicing {provider}")
        services = Service \
            .select() \
            .join(ServiceCustomer) \
            .execute()

        string_wr = io.StringIO()
        csv_writer = csv.writer(string_wr, delimiter=';')

        invoice = Invoice.create(
            invoice_date=datetime.date.today(),
            amount=0,
            usage=0,
            provider=provider
        )

        for key, services_by_customer_group in groupby(
                services,
                lambda service: (service.service_customer.account_owner_email, service.service_customer.cost_center)
            ):
            services_by_customer = list(services_by_customer_group)
            services = []

            additional_invoice_positions = AdditionalInvoicePosition \
                .select() \
                .where(AdditionalInvoicePosition.provider == provider) \
                .where(AdditionalInvoicePosition.service_customer == services_by_customer[0].service_customer) \
                .where(AdditionalInvoicePosition.invoice.is_null()) \
                .execute()
            remaining_discount = sum(additional_invoice_position.amount for additional_invoice_position in additional_invoice_positions)

            for service in services_by_customer:
                output = Invoicer. \
                    __invoice_service_for_customer(csv_writer, service, invoice, remaining_discount)

                remaining_discount = max(0, remaining_discount - output['cost'])
                services.append(output)

            for additional_invoice_position in additional_invoice_positions:
                if invoice.amount >= additional_invoice_position.amount:
                    invoice.amount += additional_invoice_position.amount
                    services.append({
                        'name' : additional_invoice_position.reason,
                        'cost' : additional_invoice_position.amount
                    })

        csv_string = string_wr.getvalue().replace(" ", "")
        if invoice.amount > 0:
            invoice.output = csv_string
            invoice.save()
        else:
            print("Nothing to invoice")
            invoice.delete_instance()

        Invoicer.export_csv(provider, csv_string)

        # Mark Resources as service invoiced
        Resource \
            .update(service_invoice = invoice) \
            .where(Resource.service_component.is_null(False)) \
            .execute()

        AdditionalInvoicePosition \
            .update(invoice = invoice) \
            .where(AdditionalInvoicePosition.provider == provider) \
            .where(AdditionalInvoicePosition.invoice.is_null()) \
            .execute()

        return csv_string

    def __invoice_service_for_customer(csv_writer, service, invoice, discount):
        service_components2service = service.get_servicecomponents2service()

        service_component_ids = [sc2s.service_component.id for sc2s in service_components2service]
        resource_costs = service.get_resource_costs(service_component_ids)

        # sum costs
        amount = service.get_costs(service_components2service, resource_costs)

        # add csv to email if there are any resources
        if len(resource_costs) > 0:
            cost_csv = io.StringIO()
            # Remove RelativePriceAmount key because it may cause confusion
            cpy_list = []
            for res_cost in resource_costs:
                d_2 = copy.deepcopy(res_cost)
                del d_2['RelativePriceAmount']
                cpy_list.append(d_2)

            header = list(cpy_list[0].keys())
            local_csv_writer = csv.DictWriter(cost_csv, header, delimiter=';')
            local_csv_writer.writeheader()
            local_csv_writer.writerows(cpy_list)

        result = {
            "Account" : service.name,
            "SAP_Service_ProductNr" : service.sap_service_product_nr,
            "CostCenter" : service.service_customer.cost_center,
            "AlternativeCostCenter" : service.service_customer.cost_center,
            "Amount" : max(0, amount + discount),
            "Surcharge" : Decimal(1)
        }
        if service.charge_costs_in_invoice:
            CsvExport.export_to_csv(csv_writer, [result])
            invoice.amount += math.ceil(amount)
            invoice.usage += Decimal(
                math.fsum(
                    [math.ceil(Decimal(res.get('RelativePriceAmount'))) for res in resource_costs]
                )
            )

        return { 'name' : service.name, 'cost' : amount}

    def invoice_accounts(provider):
        print(f"Invoicing {provider}")

        accounts_query = Account \
            .select() \
            .where(Account.provider == provider) \
            .join(ServiceCustomer) \
            .order_by(ServiceCustomer.cost_center, ServiceCustomer.account_owner_email) \
            .execute()

        print("{0} Accounts found".format(len(accounts_query)))

        string_io = io.StringIO()
        csv_writer = csv.writer(string_io, delimiter=';')

        invoice = Invoice.create(
            invoice_date=datetime.date.today(),
            amount=0,
            usage=0,
            provider=provider
        )

        for key, accounts in groupby(
                accounts_query,
                lambda acc: (acc.service_customer.cost_center, acc.service_customer.account_owner_email)
            ):
            account_list = list(accounts)

            additional_invoice_positions = AdditionalInvoicePosition \
                .select() \
                .where(AdditionalInvoicePosition.provider == provider) \
                .where(AdditionalInvoicePosition.service_customer == account_list[0].service_customer) \
                .where(AdditionalInvoicePosition.invoice.is_null()) \
                .execute()

            Invoicer.__invoice_resource_for_accounts(
                csv_writer,
                provider,
                account_list,
                invoice,
                additional_invoice_positions
            )

        AdditionalInvoicePosition \
            .update(invoice = invoice) \
            .where(AdditionalInvoicePosition.provider == provider) \
            .where(AdditionalInvoicePosition.invoice.is_null()) \
            .execute()

        csv_string = string_io.getvalue().replace(" ", "")
        if invoice.amount > 0:
            invoice.output = csv_string
            invoice.save()
        else:
            print("Nothing to invoice")
            invoice.delete_instance()

        Invoicer.export_csv(provider, csv_string)

        return csv_string

    @classmethod
    def export_csv(cls, provider, csv_string):
        if os.getenv('SAVE_CSV_TO_FILE', "False") == 'True':
            f = open(f"{provider}.csv", "w")
            f.write(csv_string)
            f.close()

        if os.getenv('UPLOAD_CSV') == 'True':
            try:
                Invoicer.upload_file(csv_string, provider)
            except requests.exceptions.SSLError as exc:
                email = Email()
                email.set_fromaddr(os.environ['CCOE_EMAIL'])
                email.set_body_string(str(exc))
                email.set_toaddr(os.environ['CCOE_EMAIL'])
                email.set_subject("Failed CSV Upload " + provider)
                email.add_cost_csv(csv_string, provider + '.csv', zip_file=False)
                email.send()

    @classmethod
    def __invoice_resource_for_accounts(cls, csv_writer, provider, accounts, invoice, additional_invoice_positions):
        query = (Resource \
            .select(
                Account.account_name.alias('Account'),
                Account.sap_service_product_nr.alias('SAP_Service_ProductNr'),
                Resource.cost_center.alias('AlternativeCostCenter'),
                ServiceCustomer.cost_center.alias('CostCenter'),
                fn.SUM(Resource.cost).alias('Amount'),
                Account.percentage_charge.alias('Surcharge')
            ) \
            .join(Account) \
            .where(Account.provider == provider) \
            .join(ServiceCustomer) \
            .where(Resource.account.in_(accounts)) \
            .where(Resource.invoice.is_null()) \
            .group_by(Account.account_name, Resource.cost_center, ServiceCustomer.cost_center)) \
            .dicts()

        total_additional_invoice_positions = Decimal(sum(
            additional_invoice_position.amount for additional_invoice_position in additional_invoice_positions
        ))

        CsvExport.export_to_csv(csv_writer, query, total_additional_invoice_positions)

        invoice.amount += Decimal(
            math.fsum(
                [math.ceil(Decimal(res.get('Amount'))*res.get('Surcharge')) for res in query]
        ))
        invoice.amount = max(0, Decimal(invoice.amount) + total_additional_invoice_positions)

        invoice.usage += Decimal(math.fsum([Decimal(res.get('Amount')) for res in query]))

        Resource \
            .update(invoice = invoice) \
            .where(Resource.account.in_(accounts)) \
            .where(Resource.invoice.is_null()) \
            .execute()

        if invoice.amount > 0:
            invoice.save()

    def __upload_file(csv_string, provider):
        comadapter_user = get_secret(f'{provider}_comadapter_user')
        comadapter_pw = get_secret(f'{provider}_comadapter_pw')
        url = get_secret(f'{provider}_comadapter_url')
        headers = {'content-type': 'octet-stream'}
        upload = requests.post(
            url,
            data=str(csv_string).encode('utf-16'),
            headers=headers,
            auth=(comadapter_user, comadapter_pw),
            verify=False
        )
        if not upload.status_code == 200:
            raise Exception('Fileupload failed with status code ' + str(upload.status_code) + '!')

    # Fix for Old SSL Certs on certain systems with errors like: [SSL: DH_KEY_TOO_SMALL] dh key too small
    def upload_file(csv_string, provider):
        requests.packages.urllib3.disable_warnings()
        requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
        Invoicer.__upload_file(csv_string, provider)