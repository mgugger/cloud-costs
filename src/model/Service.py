import datetime
import math
import decimal
from peewee import JOIN, Model, TextField, ForeignKeyField, fn, BooleanField
from src.settings import Settings
from src.model.ServiceCustomer import ServiceCustomer
from src.model.ServiceType import ServiceType

class Service(Model):
    name = TextField()
    description = TextField(null=True)
    sap_service_product_nr = TextField(null=True)
    service_customer = ForeignKeyField(ServiceCustomer, null=True, default=None, index=True)
    service_type = ForeignKeyField(ServiceType, null=True, default=None, index=True)
    charge_costs_in_invoice = BooleanField(default=True)

    def __str__(self):
        return str(self.name)

    def get_servicecomponents2service(self):
        # avoid circular imports with local import
        from src.model import ServiceComponent2Service, ServiceComponent, ServiceComponentPart

        sc2s = ServiceComponent2Service \
            .select(
                ServiceComponent2Service.id,
                ServiceComponent2Service.name,
                ServiceComponent2Service.quantity,
                ServiceComponent2Service.service_component_part_id,
                ServiceComponent.id,
                ServiceComponent.name,
                ServiceComponent.relative_price_percentage,
                ServiceComponent.fixed_service_price,
                ServiceComponent.absolute_price,
                Service.id,
                Service.name,
                ServiceComponentPart.service_component_id,
                ServiceComponentPart.price_per_unit,
                ServiceComponentPart.service_component_price_percentage,
                ServiceComponentPart.id,
                ServiceComponentPart.name) \
            .where(ServiceComponent2Service.service == self) \
            .join(ServiceComponent) \
            .switch(ServiceComponent2Service) \
            .join(ServiceComponentPart, JOIN.LEFT_OUTER) \
            .switch(ServiceComponent2Service) \
            .join(Service) \
            .execute()

        return sc2s

    def get_resource_costs(self, service_component_ids, invoices = []):
        from src.model import ServiceComponent2Service, ServiceComponent, Resource, DataImport, ServiceComponentPart

        today = datetime.date.today()
        first_day = today.replace(day=1)

        query = ServiceComponent \
            .select(
                Service.name.alias('Service'),
                ServiceComponent2Service.id.alias('ServiceComponent2ServiceId'),
                ServiceComponent2Service.name.alias('ServicePart'),
                ServiceComponent2Service.quantity.alias('Quantity'),
                ServiceComponent.name.alias('ServiceComponent'),
                ServiceComponent.id.alias('ServiceComponentId'),
                ServiceComponent.absolute_price.alias('AbsolutePrice'),
                ServiceComponent.relative_price_percentage.alias('RelativePricePercentage'),
                (ServiceComponent2Service.quantity * ServiceComponent.absolute_price).alias('AbsoluteTotalPrice'),
                fn.SUM(Resource.cost).alias('RelativePriceAmount'),
                ServiceComponentPart.service_component_price_percentage.alias('ServiceComponentPartPercentage'),
                ServiceComponentPart.price_per_unit.alias('ServiceComponentPartPricePerUnit'),
                ServiceComponentPart.id.alias('ServiceComponentPartId')
            ) \
            .where(ServiceComponent.id.in_(service_component_ids)) \
            .join(ServiceComponent2Service) \
            .where(ServiceComponent2Service.service == self) \
            .join(Service) \
            .switch(ServiceComponent2Service) \
            .join(ServiceComponentPart, JOIN.LEFT_OUTER) \
            .switch(ServiceComponent) \
            .join(Resource) \
            .join(DataImport) \
            .where((Resource.service_invoice.is_null()) | (Resource.service_invoice.in_(invoices))) \
            .where(DataImport.start_time >= first_day) \
            .group_by(ServiceComponent2Service.name, ServiceComponentPart.id) \

        return query.dicts().execute()

    def get_costs(self, service_components2service, resource_costs, add_absolute_costs=True, add_fixed_price=True):
        amount = decimal.Decimal(0)
        # add fixed service price if sc2s is not part of a separate service component part
        if add_absolute_costs:
            absolute_costs_elements = [
                    sc2s for sc2s in service_components2service \
                        if sc2s.service_component.absolute_price and \
                            not (sc2s.service_component_part and sc2s.service_component_part.price_per_unit)
            ]
            amount += decimal.Decimal(math.fsum([(sc2s.service_component.absolute_price) \
                    * sc2s.quantity \
                    * (sc2s.service_component_part.service_component_price_percentage / decimal.Decimal(100) if sc2s.service_component_part and sc2s.service_component_part.service_component_price_percentage else 1)\
                        for sc2s in absolute_costs_elements]))

        # add fixed service price if sc2s is not part of a separate service component part
        if add_fixed_price:
            fixed_service_prices = [
                sc2s for sc2s in service_components2service if sc2s.service_component.fixed_service_price and not sc2s.service_component_part
            ]
            amount += decimal.Decimal(math.fsum([sc2s.service_component.fixed_service_price for sc2s in fixed_service_prices]))

        # add variable service price for service component part
        variable_price_parts = [
            sc2s for sc2s in service_components2service \
                if sc2s.service_component_part and sc2s.service_component_part.price_per_unit
        ]
        amount += decimal.Decimal(math.fsum([sc2s.service_component_part.price_per_unit * decimal.Decimal(sc2s.quantity) for sc2s in variable_price_parts]))

        for resource_cost in resource_costs:
            if resource_cost.get('RelativePriceAmount') and resource_cost.get('RelativePricePercentage'):
                relevant_sc2s = [sc2s for sc2s in service_components2service \
                    if sc2s.service_component_id == resource_cost.get('ServiceComponentId') \
                    and sc2s.service_component_part_id == resource_cost.get('ServiceComponentPartId') \
                    and sc2s.id == resource_cost.get('ServiceComponent2ServiceId')]
                if  resource_cost.get('ServiceComponentPartPercentage'):
                    rel_price_amount = decimal.Decimal(resource_cost.get('RelativePriceAmount'))
                    service_component_percentage = decimal.Decimal(resource_cost.get('RelativePricePercentage')) / 100
                    part_percentage = decimal.Decimal(resource_cost.get('ServiceComponentPartPercentage')) / 100
                    quantity = next((decimal.Decimal(sc2s.quantity) for sc2s in relevant_sc2s \
                        if sc2s.service_component_part), 0)
                    sum_to_add = rel_price_amount * part_percentage * quantity * service_component_percentage
                    amount += sum_to_add
                # Only add relative price from resource costs if it is not overriden by price_per_unit in component part
                # Otherwise it multiple times add the base price
                elif not resource_cost.get('ServiceComponentPartPricePerUnit'):
                    amount += decimal.Decimal(resource_cost.get('RelativePriceAmount')) \
                        * (decimal.Decimal(resource_cost.get('RelativePricePercentage')) / 100) \
                        * next((decimal.Decimal(sc2s.quantity) for sc2s in relevant_sc2s), 0)

        return math.ceil(amount)

    def get_detailed_costs(self, invoices = [], service_components2service = None):
        if not service_components2service:
            service_components2service = self.get_servicecomponents2service()
        service_component_ids = [sc2s.service_component.id for sc2s in service_components2service]
        resource_costs = self.get_resource_costs(service_component_ids, invoices)
        results = []
        for sc2s in service_components2service:
            result = {}

            relevant_resource_costs = [resource_cost for resource_cost in resource_costs
                if resource_cost['ServiceComponentPartId'] == sc2s.service_component_part_id
            ]

            if sc2s.service_id:
                result['Service'] = sc2s.service.name
            else:
                result['Service'] = None
            result['ServicePart'] = sc2s.name
            result['ServiceComponent'] = sc2s.service_component.name
            base_price = ""
            if sc2s.service_component_part_id and sc2s.service_component_part.price_per_unit:
                base_price = f"{sc2s.service_component_part.price_per_unit} ({sc2s.service_component_part.name})"
            elif sc2s.service_component_part_id and sc2s.service_component_part.service_component_price_percentage and sc2s.service_component.absolute_price:
                base_price = f"{sc2s.service_component.absolute_price}*{sc2s.service_component_part.service_component_price_percentage}% ({sc2s.service_component_part.name})"
            elif sc2s.service_component.absolute_price:
                base_price = f"{sc2s.service_component.absolute_price}"
            result['UnitPrice'] = base_price
            result['Quantity'] = sc2s.quantity

            if sc2s.service_component.relative_price_percentage and sc2s.service_component_part and sc2s.service_component_part.service_component_price_percentage:
                costs = self.get_costs([sc2s], relevant_resource_costs, add_absolute_costs=False, add_fixed_price=False),
                result['RelativePrice'] = f"{costs} ({sc2s.service_component.relative_price_percentage}%, {sc2s.service_component_part.name}*{sc2s.service_component_part.service_component_price_percentage}%)"

            elif sc2s.service_component.relative_price_percentage and sc2s.service_component_part and not sc2s.service_component_part.price_per_unit:
                costs = self.get_costs([sc2s], relevant_resource_costs, add_absolute_costs=False, add_fixed_price=False)
                result['RelativePrice'] = f"{costs} ({sc2s.service_component.relative_price_percentage}%)"

            elif sc2s.service_component.relative_price_percentage:
                try:
                    costs = self.get_costs([sc2s], relevant_resource_costs, add_absolute_costs=False, add_fixed_price=False)
                    result['RelativePrice'] = f"{costs} ({sc2s.service_component.relative_price_percentage}%)"
                except:
                    pass

            if sc2s.service_component.fixed_service_price and not sc2s.service_component_part:
                result['FixedPrice'] = decimal.Decimal(sc2s.service_component.fixed_service_price)

            result['TotalPrice'] = self.get_costs(
                [sc2s],
                relevant_resource_costs,
                add_absolute_costs=True,
                add_fixed_price=True
            )
            results.append(result)
        return results

    class Meta:
        database = Settings().db
