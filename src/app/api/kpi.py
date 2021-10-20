import io
import csv

from flask import Blueprint, jsonify, make_response

from peewee import JOIN
from src.model import Invoice

kpi_api = Blueprint('kpi', __name__, template_folder='templates')

@kpi_api.route('/kpi/csv')
def get_kpi_csv():
    invoice_alias = Invoice.alias()

    invoice_costs = Invoice\
        .select(Invoice.provider.alias('kpi'), Invoice.date, Invoice.amount) \
        .join(invoice_alias, JOIN.LEFT_OUTER, 
            on=((Invoice.date < invoice_alias.date) &(Invoice.provider == invoice_alias.provider))
        ) \
        .where(invoice_alias.id.is_null()) \
        .dicts()

    string_io = io.StringIO()
    header = ['kpi', 'date', 'amount']
    dict_writer = csv.DictWriter(string_io, header, delimiter=';')
    dict_writer.writeheader()
    dict_writer.writerows(invoice_costs)
    output = make_response(string_io.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=kpi.csv"
    output.headers["Content-type"] = "text/csv"

    return output

@kpi_api.route('/kpi/json')
def get_kpi_json():
    invoice_alias = Invoice.alias()

    invoice_costs = Invoice\
        .select(Invoice.provider.alias('kpi'), Invoice.date, Invoice.amount) \
        .join(invoice_alias, JOIN.LEFT_OUTER, 
            on=((Invoice.date < invoice_alias.date) &(Invoice.provider == invoice_alias.provider))
        ) \
        .where(invoice_alias.id.is_null()) \
        .dicts()

    result = []
    for i in invoice_costs:
        result.append(i)

    return jsonify(result)
