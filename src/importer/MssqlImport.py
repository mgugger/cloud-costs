import math
import datetime
import pyodbc
from src.importer.ImportBase import ImportBase
from src.model import ServiceComponent2Service, ServiceComponent
from dateutil.relativedelta import relativedelta

TODAY = datetime.date.today() + relativedelta(months=+1)

class MssqlImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.SECRETS = [

            f"{self.job_name}_user",
            f"{self.job_name}_password"
        ]

        self.PARAMETER = [
            f"{self.job_name}_server",
            f"{self.job_name}_service_component"
        ]

    def get_files(self):
        return ["MssqlImport{0}{1}".format(TODAY.strftime("%Y%m%d"), self.job_name)]

    def run_import(self, file_to_import):
        server = self.get_param(self.PARAMETER[0])
        database = 'master'
        username = self.get_secret(self.SECRETS[0])
        password = self.get_secret(self.SECRETS[1])

        cnxn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};PORT=1433;SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
        cursor = cnxn.cursor()

        databases = ("""
            with fs
            as
            (
                select database_id, type, size * 8.0 / 1024 size
                from sys.master_files
            )
            select
                name,
                (select sum(size) from fs where type = 0 and fs.database_id = db.database_id) DataFileSizeMB,
                (select sum(size) from fs where type = 1 and fs.database_id = db.database_id) LogFileSizeMB
            from sys.databases db
        """)

        cursor.execute(databases)
        for databases in cursor:
            yield {
                "name": databases[0],
                "data_size": databases[1],
                "log_size": databases[1]
            }

    def get_resources(self, import_data):
        databases = list(import_data)
        total_db_size = sum(db["data_size"] + db["log_size"] for db in databases)
        print(total_db_size)

        service_component_name = self.get_param(self.PARAMETER[1])
        service_component = ServiceComponent.get_or_none(name = service_component_name)
        if not service_component:
            service_component = ServiceComponent.create(name = service_component_name)

        service = None

        for database in databases:
            if database['name'] not in ["master", "model", "tempdb", "msdb"]:
                service_component_quantity = \
                    math.ceil(float(database['data_size'] + database['log_size']) / float(total_db_size) * 100)/100
                service_component2_service = ServiceComponent2Service.get_or_none(
                    name = database['name'],
                    service_component = service_component
                )
                if not service_component2_service:
                    service_component2_service = ServiceComponent2Service.create(
                        name = database['name'],
                        quantity=service_component_quantity,
                        service_component = service_component,
                        service = service
                    )
                else:
                    service_component2_service.quantity = service_component_quantity
                    service_component2_service.save()

        databases_names = [database['name'] for database in databases]
        ServiceComponent2Service.delete() \
            .where(ServiceComponent2Service.service_component == service_component) \
            .where(ServiceComponent2Service.name.not_in(databases_names)) \
            .execute()

        return []