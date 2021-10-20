import abc

class MapperBase(object):
    __metaclass__ = abc.ABCMeta
    
    mappings=None
   
    def set_mappings(self, mappings):
        self.mappings=mappings

    @abc.abstractmethod
    def get_resources_as_dicts(self, data):
        return
