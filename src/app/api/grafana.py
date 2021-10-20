from itertools import groupby, accumulate
from datetime import datetime, timedelta
import dateutil.relativedelta
from flask import Blueprint,jsonify,request
import simplejson as json
from src.model import Invoice,ServiceCustomer
from src.settings import Settings
from src.constants import Constants

grafana_api = Blueprint('grafana', __name__, template_folder='templates')

def convert_to_datetime(timestamp):
    return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

@grafana_api.route('/grafana')
def get_grafana():
    return 'This datasource is healthy.'

@grafana_api.route('/grafana/search', methods=['POST'])
def get_grafana_search():
    return jsonify(['usage', 'usage_accumulated', 'account_cost_by_kst', 'service_cost_by_kst'])

@grafana_api.route('/grafana/query', methods=['POST'])
def get_grafana_query():
    req = request.get_json()
    from_datetime = convert_to_datetime(req['range']['from'])
    to_datetime = convert_to_datetime(req['range']['to'])
    target = req['targets'][0]['target']
    last_month = (datetime.now() - dateutil.relativedelta.relativedelta(months=1)).replace(day=1)

    invoices = Invoice \
        .select() \
        .where(Invoice.date > from_datetime) \
        .where(Invoice.date < to_datetime) \
        .order_by(Invoice.provider, Invoice.date) \
        .execute()

    data = []

    if target == 'usage':
        for provider, invoices in groupby(invoices, lambda x: x.provider):
            data.append(
                {
                    "target": provider,
                    "datapoints": [[inv.usage, inv.date.replace(day=1).timestamp() * 1000] for inv in list(invoices)]
                }
            )
    elif target == 'usage_accumulated':
        # TODO do not hardcode values
        target_start = datetime(2020, 7, 1, 00, 00)
        target_end = datetime(2025, 7, 1, 00, 00)
        target = 20000000
        data = data + add_target("Azure Contract", target_end, target_start, target)

        target_start = datetime(2020, 9, 1, 00, 00)
        target_end = datetime(2024, 9, 1, 00, 00)
        target = 5000000
        data = data + add_target("GCP Contract", target_end, target_start, target)

        for provider, invoices in groupby(invoices, lambda x: x.provider):
            invoice_list = list(invoices)
            amounts = [inv.usage for inv in invoice_list if inv.usage]
            timestamps = [inv.date.replace(day=1).timestamp() * 1000 for inv in invoice_list]
            amounts_acc = list(accumulate(amounts))
            amounts_acc_list = list(map(lambda x,y: [x, y], amounts_acc, timestamps))
            data.append(
                {
                    "target": provider + " Usage",
                    "datapoints": amounts_acc_list
                }
            )
    elif target == 'account_cost_by_kst':
        latest_invoices = Invoice \
            .select() \
            .where(Invoice.date > last_month) \
            .where(Invoice.provider != Constants.ManagedCloudServices) \
            .order_by(Invoice.provider, Invoice.date) \
            .execute()

        data = data + costs_by_kst(latest_invoices)

    elif target == 'service_cost_by_kst':
        latest_invoices = Invoice \
            .select() \
            .where(Invoice.date > last_month) \
            .where(Invoice.provider == Constants.ManagedCloudServices) \
            .order_by(Invoice.provider, Invoice.date) \
            .execute()

        data = data + costs_by_kst(latest_invoices)

    return json.dumps(data)

def add_target(name, target_end, target_start, target):
    data = []
    days_until_target = range((target_end - target_start).days)
    daily_increment = target / len(days_until_target)

    target_datapoints = []
    for val in days_until_target:
        target_datapoints.append(
            [val*daily_increment, (target_start + timedelta(days=val)).timestamp() * 1000]
        )

    data.append({
        "target": name,
        "datapoints": target_datapoints
        }
    )
    return data

def costs_by_kst(latest_invoices):
    lines = []
    data = []
    service_customers = ServiceCustomer.select().dicts().execute()
    service_customers_by_kst = { svc['cost_center'] : svc['name'] for svc in service_customers }
    for invoice in latest_invoices:
        lines += [line.split(';') for line in invoice.output.split('\n') if len(line.split(';')) > 4]
    columns = [
            { "text" : "KST", "type" : "string" },
            { "text" : "Service", "type" : "string" },
            { "text" : "CHF", "type" : "number" }
        ]
    table_rows = []
    for line in lines:
        service_customer = service_customers_by_kst.get(line[1], line[1])
        table_rows.append(
            [service_customer, "{0} ({1})".format(Settings().get_provider_from_sap_service_product_nr(line[3]), line[3]), int(line[4])]
        )
    data.append(
        {
            "columns": columns,
            "rows": table_rows,
            "type": "table"
        }
    )

    return data
