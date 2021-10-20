from peewee import fn
from src.model.Resource import Resource
from src.model.Invoice import Invoice
from src.settings import Settings

class DatabaseCompressor():
    @classmethod
    def compress(cls):
        last_invoices = Invoice\
            .select() \
            .group_by(Invoice.provider) \
            .having(Invoice.date == fn.MAX(Invoice.date)) \

        print(f"found {len(last_invoices)} to compress")

        for invoice in last_invoices:
            print(f"compressing resources in invoice {invoice.provider} from {invoice.date}")
            with Settings().db.atomic():
                grouped_resources = Resource \
                    .select(
                        fn.GROUP_CONCAT(Resource.id).coerce(False).alias('resource_ids'),
                        fn.SUM(Resource.cost).alias('cost'),
                        fn.SUM(Resource.quantity).alias('quantity'),
                        Resource.service,
                        Resource.category,
                        Resource.region,
                        Resource.tags,
                        Resource.cost_center,
                        Resource.term,
                        Resource.account,
                        Resource.invoice,
                        Resource.service_invoice,
                        Resource.service_component,
                        Resource.data_import) \
                    .where(Resource.invoice == invoice) \
                    .group_by(
                        Resource.service,
                        Resource.category,
                        Resource.region,
                        Resource.tags,
                        Resource.cost_center,
                        Resource.term,
                        Resource.account,
                        Resource.invoice,
                        Resource.service_invoice,
                        Resource.service_component,
                        Resource.data_import) \
                    .execute()
                print("grouped {no_resources}".format(no_resources=len(grouped_resources)))

                for grouped_resource in grouped_resources:
                    Resource \
                        .delete() \
                        .where(Resource.id.in_(grouped_resource.resource_ids.split(','))) \
                        .execute()

                    Resource.create(
                        service=grouped_resource.service,
                        category=grouped_resource.category,
                        region=grouped_resource.region,
                        tags=grouped_resource.tags,
                        cost_center=grouped_resource.cost_center,
                        term=grouped_resource.term,
                        account=grouped_resource.account,
                        invoice=grouped_resource.invoice,
                        service_invoice=grouped_resource.service_invoice,
                        service_component=grouped_resource.service_component,
                        data_import=grouped_resource.data_import,
                        cost=grouped_resource.cost,
                        quantity=grouped_resource.quantity)
