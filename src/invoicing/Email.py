import os
import smtplib
import ssl
import zipfile
import math
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
import os
from io import BytesIO
from src.helper.Secrets import get_secret, get_param

row_template = open("./src/resources/email_row_template_plain.txt","r").read()
email_template = open("./src/resources/email_template_plain.txt","r").read()
row_template_html = open("./src/resources/email_row_template.html","r").read()
email_template_html = open("./src/resources/email_template.html","r").read()

# TODO: Refactor to jinja template
class Email(object):
    def __init__(self):
        self.msg = MIMEMultipart()
        self.csvs = []

    def set_fromaddr(self, fromaddr):
        self.fromaddr = fromaddr
        self.msg['From'] = fromaddr

    def set_toaddr(self, toaddr):
        if os.getenv('REDIRECT_EMAIL_TO_CCOE') == 'True':
            self.msg['To'] = os.environ['CCOE_EMAIL']
        else:
            self.msg['To'] = toaddr
            self.msg['Bcc'] = os.environ['CCOE_EMAIL']

    def set_subject(self, subject):
        if os.getenv('REDIRECT_EMAIL_TO_CCOE') == 'True':
            self.msg['Subject'] = "[DEBUG] " + subject
        else:
            self.msg['Subject'] = subject

    def set_body_string(self, content):
        self.body = content
        self.msg.attach(MIMEText(self.body, 'plain'))

    def set_body(self, cost_center, from_date, to_date, accounts, payg_costs, ri_costs, services, discounts):
        service_string=''.join(
            [row_template.format(
                row=service['name'],
                costs=service['cost'],
                additional_info='')
                for service in services
            ]
        )
        account_string=''.join(
            [row_template.format(
                row=f"[{account['provider']}] {account['name']}",
                costs=math.ceil(account['cost']),
                additional_info="" if not account['AlternativeCostCenter'] or account['AlternativeCostCenter'] == cost_center else f"(sep. KST {account['AlternativeCostCenter']})")
                for account in accounts
            ])

        discount_string=''.join(
            [row_template.format(
                row=f"[{discount.provider}] {discount.reason}",
                costs=str(discount.amount),
                additional_info='')
                for discount in discounts
            ])

        service_string_html=''.join(
            [row_template_html.format(
                row=service['name'],
                costs=service['cost'],
                additional_info='')
                for service in services
        ])

        account_string_html=''.join(
            [row_template_html.format(
                row=f"[{account['provider']}] {account['name']}",
                costs=math.ceil(account['cost']),
                additional_info="" if not account['AlternativeCostCenter'] or account['AlternativeCostCenter'] == cost_center else f"(sep. KST {account['AlternativeCostCenter']})")
                for account in accounts
            ])

        discount_string_html=''.join(
            [row_template_html.format(
                row=f"[{discount.provider}] {discount.reason}",
                costs=str(discount.amount),
                additional_info='')
                for discount in discounts
            ])

        self.body = email_template.format(
            return_email = os.environ['CCOE_EMAIL'],
            cost_center = cost_center,
            from_date = from_date,
            to_date = to_date,
            accounts = account_string,
            services = service_string,
            discounts = discount_string,
            payg_costs = math.ceil(payg_costs),
            ri_costs = math.ceil(ri_costs),
            total_service_costs = math.ceil(math.fsum([service['cost'] for service in services]))
        )

        self.html_body = email_template_html.format(
            return_email = os.environ['CCOE_EMAIL'],
            title = self.msg['Subject'],
            cost_center = cost_center,
            from_date = from_date,
            to_date = to_date,
            accounts = account_string_html,
            services = service_string_html,
            discounts = discount_string_html,
            payg_costs = math.ceil(payg_costs),
            ri_costs = math.ceil(ri_costs),
            total_service_costs = math.ceil(math.fsum([service['cost'] for service in services]))
        )

        self.msg.attach(MIMEText(self.html_body, 'html'))
        self.msg.attach(MIMEText(self.body, 'plain'))

    def add_attachment(self, attachment):
        self.attachment = attachment

    def add_cost_csv(self, csv_string, filename='costs.csv', zip_file=True):
        self.csvs.append(csv_string)
        if zip_file:
            file = BytesIO()
            zip_file = zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED)
            zip_file.writestr(filename, csv_string)
            zip_file.close()

            attachment = MIMEBase('application', 'zip')
            attachment.set_payload(file.getvalue())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', filename=filename + '.zip')
            self.msg.attach(attachment)
            zip_file.close()
        else:
            attachment = MIMEText(csv_string)
            attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            self.msg.attach(attachment)

    def send(self):
        port=int(get_param('smtp_port'))
        context = ssl.create_default_context()
        with smtplib.SMTP(get_param('smtp_host'), port) as server:
            server.starttls(context=context)
            server.login(get_secret('smtp_user'), get_secret('smtp_password'))
            server.send_message(self.msg)
            server.quit()
