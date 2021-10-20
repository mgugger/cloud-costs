import os
from functools import lru_cache
import json

from src.model.ServiceComponent import ServiceComponent
from src.model.ServiceComponent2Service import ServiceComponent2Service
from src.model.Service import Service

class TagHelper():
    def __init__(self):
        self.service_component_dictionary = {}
        self.service_dictionary = {}
        self.service_component_2_service_dictionary = {}

    @lru_cache(maxsize=2048)
    def get_cost_center(self, tag_string, fallback):
        if tag_string:
            json_object = json.loads(tag_string)
            if isinstance(json_object, list):
                json_object = { kv['key'] : kv['value'] for kv in json_object }

            cost_center = json_object.get('CostCenter', fallback)
            if not cost_center:
                cost_center = json_object.get('costcenter', fallback)
            if (cost_center != 'TODO' or cost_center == 'TestCostCenterTag'):
                return cost_center
        return fallback

    def get_service(self, tag_string):
        if tag_string:
            json_object = json.loads(tag_string)
            if isinstance(json_object, list):
                json_object = { kv['key'] : kv['value'] for kv in json_object }

            service_name = json_object.get(os.environ['billing-service-tag'], None)
            if not service_name:
                service_name = json_object.get(os.environ['billing-service-tag'], None)
            if service_name:
                service = self.service_dictionary.get(
                    service_name,
                    Service.get_or_none(name = service_name)
                )
                if not service:
                    service = Service.create(name = service_name)
                    self.service_dictionary[service_name] = service
                    service.save()
                return service
        
        return None


    def get_service_component(self, tag_string):
        if tag_string:
            json_object = json.loads(tag_string)
            if isinstance(json_object, list):
                json_object = { kv['key'] : kv['value'] for kv in json_object }

            service_component_name = json_object.get(os.environ['billing-service-component-tag'], None)
            if not service_component_name:
                service_component_name = json_object.get(os.environ['billing-service-component-tag'], None)
            service_name = json_object.get('billing-service', None)
            if not service_name:
                service_name = json_object.get('billing-service', None)

            service = None
            service_component_2_service = None
            service_component = None

            if service_component_name:
                service_component = self.service_component_dictionary.get(
                    service_component_name,
                    ServiceComponent.get_or_none(name = service_component_name)
                )

            if service_component_name and not service_component:
                service_component = ServiceComponent.create(
                    name = service_component_name,
                    relative_price_percentage = 105
                )
                self.service_component_dictionary[service_component_name] = service_component
                service_component.save()

            if service_name and service_component_name:
                service = self.get_service(tag_string)
                service_component_2_service = self.service_component_2_service_dictionary.get(
                    f"{service_component_name}_{service_name}",
                    ServiceComponent2Service.get_or_none(
                        service_component = service_component,
                        service = service
                    ))

            if service and not service_component_2_service:
                service_component_2_service = ServiceComponent2Service.create(
                    name = service_component_name,
                    quantity = 1,
                    service = service,
                    service_component = service_component
                )
                self.service_component_2_service_dictionary[f"{service_component_name}_{service_name}"] = service_component_2_service
                service_component_2_service.save()

            return service_component
        else:
            return None

    def get_service_component_by_name(self, service_component_name):
        # TODO: AWS Import does not currently check for billing-service Tag
        if service_component_name:
            service_component = self.service_component_dictionary.get(
                service_component_name,
                ServiceComponent.get_or_none(
                    name = service_component_name
            ))
            if not service_component:
                service_component = ServiceComponent.create(
                    name = service_component_name,
                    relative_price_percentage = 105
                )
                self.service_component_dictionary[service_component_name] = service_component
                service_component.save()
            return service_component
        else:
            return None