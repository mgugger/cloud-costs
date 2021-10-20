import math
from decimal import Decimal

from flask_admin import BaseView, expose
from flask import request
from src.model import Invoice
from src.helper.User import current_user

class InvoiceDetailView(BaseView):
    def is_accessible(self):
        return current_user() is not None

    @expose('/')
    def index(self):
        invoice_id = request.args.get('invoice_id', None)
        lines = []
        invoice = None
        line_total = 0
        if invoice_id:
            invoice = Invoice.get(Invoice.id == int(invoice_id))
            lines = [line.split(';') for line in invoice.output.split('\n')]
            line_total = math.fsum([Decimal(line[4]) for line in lines if len(line) > 4])

        invoices = Invoice.select(
            Invoice.date,
            Invoice.provider,
            Invoice.id
        ).order_by(Invoice.date.desc()).execute()

        return self.render('invoicedetail.html',
            invoices=invoices,
            lines=lines,
            selected_invoice_id=invoice_id,
            total_costs= invoice.amount if invoice else 0,
            str=str,
            line_total=line_total
        )
