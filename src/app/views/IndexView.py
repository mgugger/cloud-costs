import math
import datetime
import re
from flask_admin import AdminIndexView, expose
from flask import request
from peewee import fn, JOIN
from src.model import Account, Service, ServiceCustomer, ServiceComponent, ServiceComponent2Service, Resource, DataImport, Job
from src.helper.User import current_user_roles

class IndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if "admin" not in current_user_roles():
            return self.render('index_empty.html')

        imported_invoices = Account \
            .select(Account.provider, fn.SUM(Resource.cost).alias('amount'), DataImport.end_time.alias('last_import_date')) \
            .join(Resource) \
            .where(Resource.invoice.is_null()) \
            .join(DataImport) \
            .group_by(Account.provider) \
            .order_by(fn.SUM(Resource.cost).desc()) \
            .dicts()

        todos = []
        accounts_without_customer = Account \
            .select() \
            .where(Account.service_customer is None) \
            .count()
        if accounts_without_customer > 0:
            todos.append({
                "name": "Missing ServiceCustomer in Account",
                "description": f"{accounts_without_customer} Account(s) without ServiceCustomer assigned"
            })

        services_without_customer = Service \
            .select() \
            .where(Service.service_customer is None) \
            .count()
        if services_without_customer > 0:
            todos.append({
                "name": "Missing ServiceCustomer in Service",
                "description": f"{services_without_customer} Service(s) without assigned ServiceCustomer"
            })
        service_component_without_service = ServiceComponent \
            .select() \
            .join(ServiceComponent2Service, JOIN.LEFT_OUTER) \
            .where(ServiceComponent2Service.id.is_null()) \
            .count()
        if service_component_without_service > 0:
            todos.append({
                "name": "Unattached ServiceComponent",
                "description": f"{service_component_without_service} ServiceComponent(s) with missing ServiceComponent2Service connection"
            })

        sc2s_without_service = ServiceComponent2Service \
            .select() \
            .where(ServiceComponent2Service.service_id.is_null()) \
            .count()
        if sc2s_without_service > 0:
            todos.append({
                "name": "Unattached ServiceComponent2Service",
                "description": f"{sc2s_without_service} ServiceComponent2Service(s) without assigned Service"
            })

        regex = re.compile(r'[\d]{7}-\d{10}$')
        service_customer_dict = ServiceCustomer.select(ServiceCustomer.cost_center).dicts()
        invalid_costcenters = [
            x['cost_center']
            for x in service_customer_dict
            if x['cost_center'] and not regex.match(x['cost_center'])
        ]
        if len(invalid_costcenters) > 0:
            todos.append({
                "name": "Wrong CostCenter",
                "description": f"{len(invalid_costcenters)} ServiceCustomer(s) with invalid cost center: {invalid_costcenters}"
            })

        data_imports_this_month = DataImport.select(DataImport.data_import_key) \
            .where(DataImport.start_time > datetime.date.today().replace(day=1)) \
            .execute()
        data_imports_this_month = [x.data_import_key.split('/')[0] for x in data_imports_this_month]
        jobs = Job.select(Job.name).where(Job.name.not_in(data_imports_this_month)).execute()
        if len(jobs) > 0:
            todos.append({
                "name": "Data Import Jobs did not run this month",
                "description": [j.name for j in jobs]
            })

        return self.render('index_view.html',
            imported_invoices=imported_invoices,
            request_headers=request.headers,
            todos=todos,
            math=math
        )
