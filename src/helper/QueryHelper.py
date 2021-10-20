from src.settings import Settings
from src.model import Resource, AdditionalInvoicePosition

def delete_invoice_helper(model):
    with Settings().db.atomic() as transaction:
        try:
            Resource.update(invoice = None) \
                .where(Resource.invoice_id == model.id).execute()
            Resource.update(service_invoice = None) \
                .where(Resource.service_invoice_id == model.id).execute()
            AdditionalInvoicePosition.update(invoice = None) \
                .where(AdditionalInvoicePosition.invoice_id == model.id).execute()
            model.delete_instance()
        except Exception as exc:
            transaction.rollback()
            raise Exception(exc) from exc
