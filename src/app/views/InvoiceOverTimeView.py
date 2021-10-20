import datetime
from flask_admin import BaseView, expose
from src.model import Invoice
from src.helper.User import current_user_roles
from dateutil.relativedelta import relativedelta
from src.helper.User import current_user

ONE_YEAR_AGO = datetime.datetime.now() - datetime.timedelta(days=365)

class InvoiceOverTimeView(BaseView):
    def is_accessible(self):
        return current_user() is not None

    @expose('/')
    def index(self):
        rows = []
        invoice = None
        invoices = Invoice \
            .select() \
            .where(Invoice.date > ONE_YEAR_AGO) \
            .order_by(Invoice.date).execute()
        for invoice in invoices:
            lines = [line.split(';') for line in invoice.output.split('\n') if len(line) >= 4]
            for line in lines:
                item_name = line[0].split("_")[0]
                amount = line[4]
                provider = invoice.provider
                kst = line[1]
                date = (invoice.date - relativedelta(months=1)).strftime("%B %Y")
                rows.append({
                    'provider': provider,
                    'date': date,
                    'name': item_name,
                    'cost_chf': amount,
                    'kst': kst
                })

        return self.render('invoiceovertimedetail.html',
            lines=rows
        )