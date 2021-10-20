import math
import datetime
from src.importer.ImportBase import ImportBase
from src.model.ServiceComponent2Service import ServiceComponent2Service
from src.model.ServiceComponent import ServiceComponent
from dateutil.relativedelta import relativedelta
import mysql.connector

TODAY = datetime.date.today() + relativedelta(months=+1)

class MysqlImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.job_name = job_name
        self.PARAMETER = [
            f"{self.job_name}_host",
            f"{self.job_name}_service_component"]
        self.SECRETS = [
            f"{self.job_name}_user",
            f"{self.job_name}_password",
        ]

    def get_files(self):
        return [f"MysqlImport{TODAY.strftime('%Y%m%d')}{self.job_name}"]

    def run_import(self, file_to_import):
        conn = mysql.connector.connect (
            user=self.get_secret(self.SECRETS[0]),
            password=self.get_secret(self.SECRETS[1]),
            host=self.get_param(self.PARAMETER[0]),
            buffered=True)

        cursor = conn.cursor()
        databases = ("""
            SELECT table_schema "DB Name",
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) "DB Size in MB"
            FROM information_schema.tables
            GROUP BY table_schema;
        """)
        cursor.execute(databases)
        for databases in cursor:
            yield {
                "name": databases[0],
                "size": databases[1]
            }

    def get_resources(self, import_data):
        databases = list(import_data)
        total_db_size = sum(db["size"] for db in databases)

        service_component_name = self.get_param(self.PARAMETER[1])
        service_component = ServiceComponent.get_or_none(name = service_component_name)
        if not service_component:
            service_component = ServiceComponent.create(name = service_component_name)

        service = None

        for database in databases:
            if database['name'] not in ["performance_schema", "mysql", "information_schema"]:
                service_component_quantity = \
                    math.ceil(float(database['size']) / float(total_db_size) * 100)/100
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
