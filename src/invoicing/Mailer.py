from itertools import groupby, chain
import io
import csv
import os
import math
from calendar import monthrange
import datetime
from dateutil.relativedelta import relativedelta
from peewee import fn, JOIN
from src.model import ServiceCustomer, Resource, Account, ServiceComponent2Service, Invoice, Service, AdditionalInvoicePosition
from src.invoicing import Email

TODAY = datetime.date.today()
FIRSTDAY = TODAY.replace(day=1)
LASTMONTH_FIRSTDAY = (FIRSTDAY - datetime.timedelta(days=1)).replace(day=1)
LASTMONTH_LASTDAY = LASTMONTH_FIRSTDAY\
    .replace(day=monthrange(LASTMONTH_FIRSTDAY.year, LASTMONTH_FIRSTDAY.month)[1])

class Mailer():
    def send_mails_with_last_billing_info(specific_service_customers = None, invoices = [], override_email = None):
        service_customers = None
        if specific_service_customers:
            service_customers = specific_service_customers
        else:
            service_customers = ServiceCustomer.select() \
                .where(ServiceCustomer.account_owner_email.is_null(False)) \
                .execute()
        print("sending {0} mails".format(len(service_customers)))
        emails = []
        for idx, service_customer in enumerate(service_customers):
            print("sending mail for {0} with index {1} out of {2} for invoices {3} to email {4}".format(
                service_customer.name,
                idx+1,
                len(service_customers),
                [invoice.id for invoice in invoices] \
                    if len(invoices) > 0 else "last month invoices",
                override_email if override_email else "service customer mail"
            ))
            email = Mailer.create_email(service_customer, invoices, override_email=override_email)
            if email:
                Mailer.send_email(email)
                emails.append(email)

        ServiceComponent2Service \
            .delete() \
            .where(ServiceComponent2Service.delete_after_invoice) \
            .execute()

        return emails

    def get_account_costs(accounts, invoices):
        query = (Resource \
            .select(
                Account.account_name.alias('name'),
                Account.provider,
                Resource.cost_center.alias('AlternativeCostCenter'),
                ServiceCustomer.cost_center.alias('CostCenter'),
                fn.SUM(Resource.cost * Account.percentage_charge).alias('cost'),
            ) \
            .join(Account) \
            .join(ServiceCustomer) \
            .where(Resource.account.in_(accounts)) \
            .where(Resource.invoice.in_(invoices)) \
            .order_by(Account.provider, Account.account_name) \
            .group_by(
                Account.account_name,
                Account.provider,
                Resource.cost_center,
                ServiceCustomer.cost_center)) \
            .dicts()

        return query

    def get_service_costs(services, invoices):
        service_costs = []
        for service in list(services):
            results = service.get_detailed_costs(invoices)

            # sum costs
            service_components2service = service.get_servicecomponents2service()
            service_component_ids = \
                [sc2s.service_component.id for sc2s in service_components2service]
            resource_costs = service.get_resource_costs(service_component_ids, invoices)
            amount = service.get_costs(service_components2service, resource_costs)

            resources = []
            for service_component in results:
                res = {
                    'service': service.name,
                    'servicePart':   service_component['ServicePart'],
                    'serviceComponent':   service_component['ServiceComponent'],
                    'quantity' : service_component['Quantity'],
                    'cost_chf' : service_component['TotalPrice'],
                    'cost_center': service.service_customer.cost_center,
                    'date': "{0}.{1}".format(invoices[0].date.year, invoices[0].date.month)
                }
                resources.append(res)
            service_costs.append({
                'name' : service.name,
                'cost' : math.ceil(amount),
                'resources': resources
            })

        return service_costs

    def add_service_csv(email, service_costs, cost_center):
        if(len(service_costs) > 0 and len(service_costs[0]['resources']) > 0):
            today = datetime.datetime.now()
            service_csv = io.StringIO()
            header = list(service_costs[0]['resources'][0].keys())
            local_csv_writer = csv.DictWriter(service_csv, header, delimiter=';')
            local_csv_writer.writeheader()
            local_csv_writer.writerows(
                chain.from_iterable([service_cost['resources'] for service_cost in service_costs])
            )
            email.add_cost_csv(
                service_csv.getvalue(),
                f"managed_cloud_shared_services_{today.month}_{ today.year}_{cost_center}.csv"
            )

    def add_cost_csv(email, accounts, invoices, provider, cost_center):
        query_payg = list(Resource \
            .select(
                Resource.service,
                Resource.category,
                Resource.region,
                Resource.quantity,
                Resource.date,
                (Resource.cost * Account.percentage_charge).alias('cost'),
                Resource.tags,
                Resource.cost_center,
                Resource.instance_id,
                Resource.term,
                Account.account_name) \
            .where(Resource.account.in_(accounts)) \
            .where(Resource.invoice.in_(invoices)) \
            .where(Resource.term.is_null()) \
            .join(Account) \
            .dicts())

        if len(query_payg) > 0:
            today = datetime.datetime.now()
            header = list(query_payg[0].keys())
            payg = io.StringIO()
            csv_writer = csv.DictWriter(payg, header, delimiter=';')
            csv_writer.writeheader()
            csv_writer.writerows(query_payg)

            email.add_cost_csv(
                payg.getvalue(),
                f"{provider}_cost_pay-as-you-go_{today.month}_{today.year}_{cost_center}.csv"
            )

        # RI
        query_ri = list(Resource \
            .select(
                Resource.service,
                Resource.category,
                Resource.region,
                Resource.date,
                Resource.quantity,
                (Resource.cost * Account.percentage_charge).alias('cost'),
                Resource.tags,
                Resource.cost_center,
                Resource.instance_id,
                Resource.term,
                Account.account_name) \
            .where(Resource.account.in_(accounts)) \
            .where(Resource.invoice.in_(invoices)) \
            .where(Resource.term.is_null(False)) \
            .join(Account) \
            .dicts())

        if len(query_ri) > 0:
            today = datetime.datetime.now()
            header = list(query_ri[0].keys())
            reserved_instance_csv = io.StringIO()
            csv_writer = csv.DictWriter(reserved_instance_csv, header, delimiter=';')
            csv_writer.writeheader()
            csv_writer.writerows(query_ri)

            email.add_cost_csv(
                reserved_instance_csv.getvalue(),
                f"{provider}_cost_reserved-instances_{today.month}_{today.year}_{cost_center}.csv"
            )

        return {
            "ri_costs": math.ceil(math.fsum([res.get('cost') for res in query_ri])),
            "payg_costs": math.ceil(math.fsum([res.get('cost') for res in query_payg]))
        }

    def create_email(service_customer, invoices = None, override_email = None):
        invoice_alias = Invoice.alias()
        if len(invoices) > 0:
            latest_invoices = invoices
        else:
            latest_invoices = list(Invoice \
                .select() \
                .join(
                    invoice_alias,
                    JOIN.LEFT_OUTER,
                    on=((Invoice.date < invoice_alias.date) &(Invoice.provider == invoice_alias.provider))
                ) \
                .where(invoice_alias.id.is_null()) \
                .execute())

        services = Service \
            .select() \
            .where(Service.service_customer == service_customer) \
            .execute()
        service_costs = Mailer.get_service_costs(services, latest_invoices)

        accounts = list(Account \
            .select() \
            .where(Account.service_customer == service_customer) \
            .execute())

        if(len(accounts) > 0 or len(services) > 0):
            email = Email()
            Mailer.add_service_csv(email, service_costs, service_customer.cost_center)
            account_costs = Mailer.get_account_costs(accounts, latest_invoices)

            ri_costs = 0
            payg_costs = 0
            for key, grouped_accounts in groupby(accounts, lambda account: account.provider):
                costs = Mailer.add_cost_csv(
                    email,
                    list(grouped_accounts),
                    latest_invoices,
                    provider=key,
                    cost_center=service_customer.cost_center
                )
                ri_costs += costs['ri_costs']
                payg_costs += costs['payg_costs']

            service_customer_discounts = AdditionalInvoicePosition \
                .select(
                    AdditionalInvoicePosition.reason,
                    AdditionalInvoicePosition.amount,
                    AdditionalInvoicePosition.provider
                ) \
                .where(AdditionalInvoicePosition.service_customer == service_customer) \
                .where(AdditionalInvoicePosition.invoice.in_(latest_invoices)) \
                .execute()

            email.set_fromaddr(os.environ['CCOE_EMAIL'])
            if override_email:
                email.set_toaddr(override_email)
            else:
                email.set_toaddr(service_customer.account_owner_email)
            email.set_subject("CloudCenterofExcellence Rechnung {0}".format("(Update)" if os.environ.get('INVOICE_UPDATE') else ""))
            if invoices:
                from_date=(min(invoices, key=lambda x: x.date).date - relativedelta(months=1)).replace(day=1).strftime("%d.%m.%Y")
                to_date=(max(invoices, key=lambda x: x.date).date.replace(day=1) - relativedelta(days=1)).strftime("%d.%m.%Y")
            else:
                from_date=LASTMONTH_FIRSTDAY.strftime("%d.%m.%Y")
                to_date=LASTMONTH_LASTDAY.strftime("%d.%m.%Y")

            email.set_body(
                service_customer.cost_center,
                from_date,
                to_date,
                account_costs,
                payg_costs=payg_costs,
                ri_costs=ri_costs,
                services=service_costs,
                discounts=service_customer_discounts
            )

            return email
        return None

    def send_email(email):
        if os.getenv('SEND_EMAILS') == 'True':
            email.send()
        else:
            print(f"Email not sent because os environ SEND_EMAILS is {os.getenv('SEND_EMAILS')}")
