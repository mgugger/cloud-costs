import csv
import io
from src.mapper.MapperBase import MapperBase

class CsvMapper(MapperBase):
    def get_resources_as_dicts(self, data, data_import, skip_rows=0):
        datastr=data
        total_rows = len(datastr)
        if skip_rows > 0:
            data = data.split('\n')[skip_rows:]
            datastr = '\n'.join(data)
        dictreader = csv.DictReader(io.StringIO(datastr))
        
        resources=[]
        for idx, row in enumerate(dictreader):
            if idx % 1000 == 0:
                print(str(idx*1000) + " processed out of " + str(total_rows))
            cost = float(self.mappings.get('cost')(row))
            if cost > float(0):
                resources.append({
                    'account':self.mappings.get('account')(row),
                    'service':self.mappings.get('service')(row),
                    'category':self.mappings.get('category')(row),
                    'region':self.mappings.get('region')(row),
                    'quantity':self.mappings.get('quantity')(row),
                    'cost': cost,
                    'tags':self.mappings.get('tags')(row),
                    'cost_center':self.mappings.get('cost_center')(row),
                    'instance_id':self.mappings.get('instance_id')(row),
                    'data_import': data_import,
                    'service_component': self.mappings.get('service_component')(row),
                    'term': self.mappings.get('term')(row),
                    'date': self.mappings.get('date')(row)
                })
        return resources
