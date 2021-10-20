import os
import math
import pytest
from peewee import fn
from src.importer.AzureImport import AzureImport
from src.model import Resource, Account, ServiceComponent
from src.tests.helper import assert_import_worked

class TestHadoopImportOnAzure(object):
    @pytest.mark.dependency()
    def test_import(self, mocker, db):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")
        azImport = AzureImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/hadoop.csv")

        assert_import_worked()
        
    @pytest.mark.dependency(depends=["TestHadoopImportOnAzure::test_import"])
    def test_calculate_total_costs(self, db):
        results = {
            'company2-portal' : 23474
        }

        res = Resource.select(fn.SUM(Resource.cost).alias('cost'), Account.account_name).join(Account).group_by(Account.account_name).dicts()
        assert len(res) > 0, "No resources have been found in result"
        for row in res:
            assert math.ceil(row['cost']) == results[row['account_name']], "Costs for {} did not match".format(row['account_name'])

    @pytest.mark.dependency(depends=["TestHadoopImportOnAzure::test_import"])
    def test_service_component_exists(self, db):
        
        res = ServiceComponent.select().execute()
        assert len(res) == 2, "2 service components should have been imported"
        assert res[1].name == "HadoopProd", "No Service Component was created from the tag"
        assert res[0].name == "HadoopPoC", "No Service Component was created from the tag"