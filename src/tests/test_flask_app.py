from src.importer.AzureImport import AzureImport
from src.invoicing import Invoicer
from src.constants import Constants

class TestFlaskApp():
    def test_home_page(self, test_client):
        response = test_client.get('/')
        assert response.status_code == 200
        assert b"Cloud Billing" in response.data

    def test_uninvoiced_accounts(self, test_client):
        response = test_client.get('/uninvoicedaccounts/')
        assert response.status_code == 200
        assert b"Provider" in response.data
    
    def test_grafana_search(self, test_client):
        response = test_client.post('/grafana/search')
        assert response.status_code == 200

    def test_grafana_query(self, mocker, db, test_client):
        mocker.patch('src.helper.Secrets.get_secret', return_value="mocktest")
        azImport = AzureImport("AzureImport")
        mocker.patch.object(azImport, 'get_secret', return_value="test mock")
        azImport.run("sample_files/azure.csv")
        Invoicer.invoice_resources(Constants.AzureProvider)

        response = test_client.post('/grafana/query',
            data="""{
                "range": {
                    "from": "2019-01-01T00:00:00.00Z",
                    "to": "2025-01-01T00:00:00.00Z"
                },
                "targets":[{
                    "target":"usage_accumulated"
                }]
            }""",
            content_type='application/json')
        assert response.status_code == 200
        assert "datapoints" in response.data.decode("utf-8")