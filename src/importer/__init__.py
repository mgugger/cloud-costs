import pkgutil, importlib, os
from src.importer.ImportBase import ImportBase

all_my_base_classes = {}
pkg_dir = os.path.dirname(__file__)
for (module_loader, name, ispkg) in pkgutil.iter_modules([pkg_dir]):
    try:
        importlib.import_module('.' + name, __package__)
    except Exception as e:
        print(e)

all_importer = {cls.__name__: cls for cls in ImportBase.__subclasses__()}