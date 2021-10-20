import os
import json
from time import strftime, localtime
import requests
from src.importer.ImportBase import ImportBase
from src.model import \
    ServiceComponent2Service, ServiceComponent, Service, ServiceComponentPart
from src.helper.Secrets import get_param
from src.constants import Constants
from src.settings import Settings

class KubeStateMetricsPrometheusImport(ImportBase):
    def __init__(self, job_name):
        super().__init__()
        self.PARAMETER = [
            f"{job_name}_prometheus_url",
            f"{job_name}_service_component"
        ]
        self.SECRETS = []
        self.job_name = job_name

    def get_files(self):
        if os.getenv('PROCESS_SAMPLE_FILES') == 'True':
            return [f"{self.job_name}_KubeStateMetricsPrometheusImport{strftime('%Y%m%d%H%M%S', localtime())}"]
        else:
            return [f"{self.job_name}_KubeStateMetricsPrometheusImport{strftime('%Y%m%d%H%M%S', localtime())}"]

    def query_prometheus(self, prome_sql):
        response = requests.get(f'{get_param(self.PARAMETER[0])}/api/v1/query',
            params={'query': prome_sql})
        resp = response.json()["data"]['result']
        return resp

    def run_import(self, file_to_import):
        prome_sql = "kube_namespace_annotations"

        resp = self.query_prometheus(prome_sql)
        result_dic = {}
        for namespace in resp:
            try:
                result_dic[namespace['metric']['namespace']] = \
                    json.loads(
                        namespace['metric']['annotation_kubectl_kubernetes_io_last_applied_configuration']
                        )['metadata']['annotations']
            except KeyError:
                result_dic[namespace['metric']['namespace']] = {}

        return result_dic

    def get_resources(self, import_data):
        service_component = ServiceComponent.get_or_none(name = get_param(self.PARAMETER[1]))
        if not service_component:
            service_component = ServiceComponent.create(name = get_param(self.PARAMETER[1]))

        for namespace in import_data.keys():
            service = None
            sc2s_name = f"{namespace}_ns"

            if import_data.get(namespace, None):
                service_name = import_data[namespace] \
                    .get('billing-service', None)
                service = Service \
                    .get_or_none(name=service_name)
                if service_name and not service:
                    service = Service.create(
                        name=service_name,
                        sap_service_product_nr=Settings().get_default_sap_service_product_nr(Constants.ManagedCloudServices),
                        description="Autocreated Service")
            service_component2_service = ServiceComponent2Service.get_or_none(
                name = sc2s_name,
                service_component = service_component
            )
            if not service_component2_service:
                service_component2_service = ServiceComponent2Service.create(
                    name = sc2s_name,
                    service_component = service_component,
                    service = service,
                    quantity = 0 # Add NS only for fixed price adds
                )
            service_component2_service.quantity = 0
            if service and not service_component2_service.service:
                service_component2_service.service = service
            service_component2_service.save()

        # GET CPU
        cpu_scp = ServiceComponentPart.get_or_none(
            service_component = service_component,
            name = "CPU"
            )
        if not cpu_scp:
            cpu_scp = ServiceComponentPart.create(
                service_component = service_component,
                name= "CPU",
                price_per_unit = 0.0001,
                description = "CPU Percentage in relation to the total amount of cpu used"
                )

        # get requests + best-effort pods with cpu shares and
        # divide by total sum to get usage percentage
        cpu_prome_query = """
        (
            sum(sum_over_time(kube_pod_container_resource_requests_cpu_cores{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by(namespace)
            or
            sum(sum_over_time(container_spec_cpu_shares{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by(namespace) / 1024
        )
        / scalar(
                sum(sum_over_time(kube_pod_container_resource_requests_cpu_cores{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by()
                or
                sum(sum_over_time(container_spec_cpu_shares{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by() / 1024
        )
        """

        cpu_resp = self.query_prometheus(cpu_prome_query)
        self.add_sc2s_part(cpu_resp, cpu_scp, import_data, service_component)

        # GET Memory
        mem_scp = ServiceComponentPart.get_or_none(
            service_component = service_component,
            name = "RAM"
            )
        if not mem_scp:
            mem_scp = ServiceComponentPart.create(
                service_component = service_component,
                name= "RAM",
                price_per_unit = 0.0001,
                description = "RAM Percentage in relation to the total amount of RAM used"
                )

        mem_prome_query = """
        (
            sum(sum_over_time(kube_pod_container_resource_requests_memory_bytes{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w] )) by(namespace)
            or
            sum(sum_over_time(container_spec_memory_limit_bytes{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by(namespace)
        )
        / scalar(
            sum(sum_over_time(kube_pod_container_resource_requests_memory_bytes{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by()
            or
            sum(sum_over_time(container_spec_memory_limit_bytes{namespace!="",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}[3w])) by()
        )
        """

        mem_resp = self.query_prometheus(mem_prome_query)
        self.add_sc2s_part(mem_resp, mem_scp, import_data, service_component)

        # GET Storage
        storageclass_query = "count(kube_persistentvolumeclaim_info) by (storageclass)"
        storageclass_resp = self.query_prometheus(storageclass_query)
        for storageclass_row in storageclass_resp:
            storageclass = storageclass_row['metric']['storageclass']
            storage_scp = ServiceComponentPart.get_or_none(
                service_component = service_component,
                name = f"storage-{storageclass}"
                )
            if not storage_scp:
                storage_scp = ServiceComponentPart.create(
                    service_component = service_component, name= f"storage-{storageclass}",
                    price_per_unit = 0.0001,
                    description = "Storage claimed in GB"
                    )
            storage_prome_query = '''
                sum (
                    sum(kube_persistentvolumeclaim_info{{storageclass=~"{0}",namespace!~"kube-system|monitoring|company2-consul-prod|company2-cloudbilling-prod|ingress-nginx|ingress-nginx-public|rundeck|company2-vault-prod|logging|velero|external-dns|external-dns-ch|cert-manager"}}) by (persistentvolumeclaim, namespace, storageclass)
                    + on (persistentvolumeclaim, namespace) group_right(storageclass)
                    sum(kube_persistentvolumeclaim_resource_requests_storage_bytes) by (persistentvolumeclaim, namespace)
                ) by (namespace) / 1024 / 1024 /1024
                '''
            storage_response = self.query_prometheus(storage_prome_query.format(storageclass))
            self.add_sc2s_part(storage_response, storage_scp, import_data, service_component)

        return []

    def add_sc2s_part(self, prom_resp, service_component_part, import_data, service_component):
        sc2s_names = []

        for namespace_metric in prom_resp:
            namespace = namespace_metric['metric']['namespace']
            value = namespace_metric['value'][-1]
            sc2s_name = f"{namespace}_{service_component_part.name}"
            sc2s_names.append(sc2s_name)
            service = None
            try:
                if import_data.get(namespace, None):
                    service_name = import_data[namespace] \
                        .get('billing-service', None)
                    service = Service \
                        .get_or_none(name=service_name)
                    if service_name and not service:
                        service = Service.create(
                            name=service_name,
                            sap_service_product_nr=Settings().get_default_sap_service_product_nr(Constants.ManagedCloudServices),
                            description="Autocreated Service")
            except KeyError:
                print(f"KeyError: {namespace} for {prom_resp}")

            service_component2_service = ServiceComponent2Service.get_or_none(
                name = sc2s_name,
                service_component = service_component,
                service_component_part = service_component_part
            )
            if not service_component2_service:
                service_component2_service = ServiceComponent2Service.create(
                    name = sc2s_name,
                    service_component = service_component,
                    service_component_part = service_component_part,
                    service = service,
                    quantity = value
                )
            service_component2_service.quantity = value
            if service and not service_component2_service.service:
                service_component2_service.service = service
            elif service and service_component2_service.service:
                service = service_component2_service.service
            service_component2_service.save()

        ServiceComponent2Service.delete() \
            .where(ServiceComponent2Service.service_component == service_component) \
            .where(ServiceComponent2Service.service_component_part == service_component_part) \
            .where(ServiceComponent2Service.name.not_in(sc2s_names)) \
            .execute()
