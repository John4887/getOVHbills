import ovh
import requests
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

# API application parameters
# Put your OVH application informatin in these variables
application_key = 'xxxxxxxxxxxxxxxx'
application_secret = 'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'
consumer_key = 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'

# Folder where bills are downloaded
# Put the folder where you want to store bills in this variable
bills_folder = '/your/folder/here'

# Create OVH customer instance
client = ovh.Client(
    endpoint='ovh-eu',
    application_key=application_key,
    application_secret=application_secret,
    consumer_key=consumer_key,
)

# Determine first day of the current month
now = datetime.now()
start_current_month = datetime(now.year, now.month, 1)

# Get current date
end_current_month = now

try:
    # Get bills list
    bills = client.get('/me/bill')

    for bill_id in bills:
        # Get bill details
        bill_details = client.get(f'/me/bill/{bill_id}')
        bill_date = datetime.strptime(bill_details['date'], '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)

        if start_current_month <= bill_date <= end_current_month:
            print(f"Downloading bill: {bill_id}")
            pdf_url = bill_details['pdfUrl']
            response = requests.get(pdf_url, stream=True)

            pdf_path = os.path.join(bills_folder, f"{bill_id}.pdf")
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

except Exception as e:
    print(f"Error: {e}")

def send_bills_by_mail(bills_folder, mail_recipient, smtp_server):
    msg = MIMEMultipart()
    msg['From'] = "sending_address@yourdomain.com"
    msg['To'] = mail_recipient
    msg['Subject'] = "Your OVH bills of the current month"
    msg.attach(MIMEText("Please find your OVH bills for the current month.", 'plain'))

    sent_files = []

    for pdf_file in os.listdir(bills_folder):
        if pdf_file.endswith(".pdf"):
            full_path = os.path.join(bills_folder, pdf_file)
            piece = MIMEBase('application', "octet-stream")
            with open(full_path, "rb") as file:
                piece.set_payload(file.read())
            encoders.encode_base64(piece)
            piece.add_header('Content-Disposition', f'attachment; filename="{pdf_file}"')
            msg.attach(piece)
            sent_files.append(full_path)

    server = smtplib.SMTP(smtp_server, 25)
    server.sendmail(msg['From'], mail_recipient, msg.as_string())
    server.quit()

    print(f"Bills sent to {mail_recipient}.")
    return sent_files

# Usage of deletion function and deletion of pdf files after sending
smtp_server = "your_smtp_server_ip_or_fqdn"
mail_recipient = "recipient_address@yourdomain.com"

sent_files = send_bills_by_mail(bills_folder, mail_recipient, smtp_server)
for full_path in sent_files:
    os.remove(full_path)
    print(f"Deleted: {full_path}")
