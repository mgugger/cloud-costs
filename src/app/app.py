from flask import Flask, render_template
from flask_admin import Admin
import os
from src.helper.Secrets import get_secret
from src.model import *
from src.settings import Settings,RecordCounter
from src.app.views import *
from src.app.api.kpi import kpi_api
from src.app.api.grafana import grafana_api
from src.app.api.auth import auth_api,oauth
from src.helper.User import current_user,current_user_roles

def _db_connect():
    try:
        Settings().db.connect(reuse_if_open=True)
    except Exception as e:
        Settings().logger.error(e)

# This hook ensures that the connection is closed when we've finished
# processing the request.
def _db_close(self):
    if not Settings().db.is_closed():
        Settings().db.close()

def context_processor():
    request_vars = {
            "sql_query_number": RecordCounter()._count,
            "user": current_user(),
            "user_roles": current_user_roles()
        }
    RecordCounter()._count = 0
    return request_vars

def handle_403(e):
    return render_template('403.html', error = e), 403

def create_app():
    app = Flask(__name__)
    oauth.init_app(app)

    app.before_request(_db_connect)
    app.context_processor(context_processor)
    app.teardown_appcontext(_db_close)
    app.register_error_handler(403, handle_403)

    application_root = os.getenv('APPLICATION_ROOT', '/')
    app.config["APPLICATION_ROOT"] = application_root

    app.secret_key = get_secret("app_secret")

    app.register_blueprint(kpi_api, url_prefix=application_root)
    app.register_blueprint(grafana_api, url_prefix=application_root)
    app.register_blueprint(auth_api, url_prefix=application_root)

    app.config['FLASK_ADMIN_SWATCH'] = 'simplex'

    admin = Admin(app, name='Cloud Billing', index_view=IndexView(url=application_root), template_mode='bootstrap4')

    admin.add_view(AccountView(Account, category="Services"))
    admin.add_view(AccountViewReadOnly(Account, category="Services", endpoint="acc_readonly"))
    admin.add_view(ServiceCustomerView(ServiceCustomer, category="Customers"))
    admin.add_view(ServiceCustomerReadOnly(ServiceCustomer, category="Customers", endpoint="sc_readonly"))
    admin.add_view(AdditionalInvoicePositionView(AdditionalInvoicePosition, category="Customers"))

    admin.add_view(ServiceView(Service, category="Services"))
    admin.add_view(ServiceViewReadOnly(Service, category="Services", endpoint="srv_readonly"))
    admin.add_view(ServiceComponent2ServiceView(ServiceComponent2Service, category="Services"))
    admin.add_view(ServiceComponent2ServiceViewReadOnly(ServiceComponent2Service, category="Services", endpoint="sc2s_readonly"))
    admin.add_view(ServiceComponentView(ServiceComponent, category="Services"))
    admin.add_view(ServiceComponentViewReadOnly(ServiceComponent, category="Services", endpoint="scomp_readonly"))
    admin.add_view(ServiceComponentPartView(ServiceComponentPart, category="Services"))

    admin.add_view(InvoiceView(Invoice, category="Import/Export"))
    admin.add_view(DataImportView(DataImport, category="Import/Export"))

    admin.add_view(UninvoicedAccounts(name='Uninvoiced Accounts', category="Stats"))
    admin.add_view(AbsoluteServiceCostEstimation(name='Service Price Estimation', category="Stats"))
    admin.add_view(ServiceComponentCosts(name='Service Component Cost', category="Stats"))
    admin.add_view(ServiceDetailView(name='Service Detail', category="Stats"))
    admin.add_view(ServiceComponentDetailView(name='Service Component Detail', category="Stats"))
    admin.add_view(InvoiceDetailView(name='Invoice Detail', category="Stats"))
    admin.add_view(InvoiceOverTimeView(name='Invoices over time', category="Stats"))
    admin.add_view(NetProfitView(name='Net Profit', category="Stats"))

    admin.add_view(JobView(Job, category="Config"))
    admin.add_view(ServiceTypeView(ServiceType, category="Config"))
    admin.add_view(ConfigView(Config, category="Config"))

    admin.add_view(ResendEmailView(name='Resend Email', category="Tools"))

    admin.add_link(LogoutMenuLink(name='Logout', category='', url="/logout"))
    admin.add_link(LoginMenuLink(name='Login', category='', url="/login/azure"))

    return app