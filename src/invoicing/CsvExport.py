import math
import csv
from decimal import Decimal
import re

kst_regex = re.compile(r'\d{7}-\d{10}$')
# add row number to export to avoid conflicts if multiple services / accounts / subscriptions have the same name
exported_rows = 0

class CsvExport(object):
    def export_to_csv(csv_writer: csv.DictWriter, query_result: list, total_additional_invoice_positions: int = 0):
        global exported_rows
        remaining_position = total_additional_invoice_positions
        for row in query_result:
            exported_rows += 1

            if Decimal(row['Amount'] <= 0):
                continue

            has_custom_costcenter_tag = row['AlternativeCostCenter'] and row['AlternativeCostCenter'] != row['CostCenter']
            cost_center = row['AlternativeCostCenter'] if has_custom_costcenter_tag and kst_regex.match(row['AlternativeCostCenter']) else row['CostCenter']

            if not kst_regex.match(cost_center):
                print("invalid kst {0} in row {1}".format(cost_center, row))
                continue

            row_amount = max(0, Decimal(row['Amount'])*row['Surcharge'] + remaining_position)
            csv_writer.writerow([
                '{account}{custom_costcenter}_{row_number}'.format(account=row['Account'], row_number=exported_rows, custom_costcenter = "(AlternativeCostCenter)" if has_custom_costcenter_tag else ""),
                cost_center,
                row.get('User', ''),
                row.get('SAP_Service_ProductNr'),
                math.ceil(row_amount),
                row.get('Comment', '')])

            if remaining_position < 0:
                remaining_position = min(0, remaining_position+Decimal(row['Amount']))
            elif remaining_position > 0:
                remaining_position = max(0, remaining_position-Decimal(row['Amount']))