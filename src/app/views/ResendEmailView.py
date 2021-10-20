from flask_admin import BaseView, expose
from flask import request
from flask import flash
from src.model import Invoice, ServiceCustomer
from src.helper.User import current_user_roles
from src.invoicing.Mailer import Mailer

class ResendEmailView(BaseView):
    def is_accessible(self):
        return "admin" in current_user_roles()

    @expose('/', methods = ['POST', 'GET'])
    def index(self):
        if request.method == 'GET':
            invoices = Invoice.select().order_by(Invoice.date.desc()).execute()
            servicecustomers = ServiceCustomer \
                .select() \
                .order_by(ServiceCustomer.name) \
                .execute()

            return self.render('resendemail.html',
                selected_invoice_id=None,
                select_servicecustomer_id=None,
                servicecustomers=servicecustomers,
                invoices=invoices,
                str=str
            )
        if request.method == "POST":
            invoice_ids = request.form.getlist('invoice_ids')
            print(invoice_ids)
            selected_invoices = list(
                Invoice.select().where(Invoice.id.in_(invoice_ids)).execute()
            )

            servicecustomer_id = request.form.get('servicecustomer_id')
            service_customer = ServiceCustomer.get_by_id(servicecustomer_id)

            override_email = request.form.get('override_email')
            print("override email: " + override_email)

            Mailer.send_mails_with_last_billing_info(
                specific_service_customers=[service_customer],
                invoices=selected_invoices,
                override_email=override_email
            )
            flash("Mail has been sent", "info")

            invoices = Invoice.select().order_by(Invoice.date.desc()).execute()
            servicecustomers = ServiceCustomer.select().order_by(ServiceCustomer.name).execute()
            return self.render('resendemail.html',
                selected_invoice_ids=invoice_ids,
                select_servicecustomer_id=servicecustomer_id,
                servicecustomers=servicecustomers,
                invoices=invoices,
                str=str
            )
