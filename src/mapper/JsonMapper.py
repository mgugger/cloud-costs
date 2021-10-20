import json
from src.mapper.MapperBase import MapperBase

"""CsvMapper maps an import string to a csv"""
class JsonMapper(MapperBase):
    def get_resources_as_dicts(self, data, data_import):
        json_data = json.loads(data)

        resources=[]
        for row in json_data:
            try:
                resources.append({
                    'account':self.mappings.get('account')(row),
                    'service':self.mappings.get('service')(row),
                    'category':self.mappings.get('category')(row),
                    'region':self.mappings.get('region')(row),
                    'quantity':self.mappings.get('quantity')(row),
                    'cost':float(self.mappings.get('cost')(row)),
                    'tags':self.mappings.get('tags')(row),
                    'cost_center':self.mappings.get('cost_center')(row),
                    'instance_id':self.mappings.get('instance_id')(row),
                    'service_component': self.mappings.get('service_component')(row),
                    'data_import' : data_import,
                    'term': self.mappings.get('term')(row),
                    'date': self.mappings.get('date')(row)
                })
            except:
                print("Could not map row:")
                print(row)
        return resources