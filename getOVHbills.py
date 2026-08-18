import ovh
import requests
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import time

# Configuration for two OVH accounts
accounts = [
    {
        "application_key": "xxxxxxxxxxxxxxxx",
        "application_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "consumer_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "bills_folder": "/folder/for/bills/storage",
        "sent_bills_file": "sent_bills_xxx.txt"
    },
    {
        "application_key": "yyyyyyyyyyyyyyyy",
        "application_secret": "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        "consumer_key": "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        "bills_folder": "/folder/for/bills/storage",
        "sent_bills_file": "sent_bills_yyy.txt"
    }
]

smtp_server = "server_ip"
mail_recipient = "mail@domain.com"


# Get current time for log purposes
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Read sent bills
def read_sent_bills(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return set(file.read().splitlines())
    except FileNotFoundError:
        return set()


# Update sent bills
def update_sent_bills(file_path, bills):
    with open(file_path, 'w', encoding='utf-8') as file:
        for bill in sorted(bills):
            file.write(f"{bill}\n")


def is_valid_pdf_content(content):
    return content.startswith(b"%PDF-")


def download_pdf_with_retry(pdf_url, pdf_path, max_attempts=10, wait_seconds=15):
    headers = {
        "User-Agent": "Mozilla/5.0 OVH-Bills-Downloader/1.0",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                pdf_url,
                headers=headers,
                timeout=(10, 60),
                allow_redirects=True
            )
            response.raise_for_status()

            content_type = (response.headers.get("Content-Type") or "").lower()
            content = response.content

            if is_valid_pdf_content(content):
                with open(pdf_path, 'wb') as f:
                    f.write(content)

                print(f"{get_current_time()}: Valid PDF downloaded: {pdf_path}")
                return True

            preview = content[:200].decode("utf-8", errors="replace").replace("\n", " ").replace("\r", " ")
            print(
                f"{get_current_time()}: Attempt {attempt}/{max_attempts} - "
                f"PDF not ready or invalid content. "
                f"Content-Type={content_type}, URL={response.url}, Preview={preview}"
            )

            last_error = ValueError("Downloaded content is not a valid PDF")

        except Exception as e:
            print(f"{get_current_time()}: Attempt {attempt}/{max_attempts} failed for {pdf_url}: {e}")
            last_error = e

        if attempt < max_attempts:
            time.sleep(wait_seconds)

    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass

    raise last_error if last_error else Exception("Unknown error during PDF download")


# Function to collect PDF paths from all accounts
def collect_pdf_paths(accounts):
    all_pdf_paths = []
    now = datetime.now()
    start_current_month = datetime(now.year, now.month, 1)

    for account in accounts:
        client = ovh.Client(
            endpoint='ovh-eu',
            application_key=account["application_key"],
            application_secret=account["application_secret"],
            consumer_key=account["consumer_key"],
        )

        sent_bills_file_path = os.path.join(account["bills_folder"], account["sent_bills_file"])
        sent_bills = read_sent_bills(sent_bills_file_path)

        try:
            bills = client.get('/me/bill')

            for bill_id in bills:
                if bill_id in sent_bills:
                    continue

                bill_details = client.get(f'/me/bill/{bill_id}')
                bill_date = datetime.strptime(
                    bill_details['date'],
                    '%Y-%m-%dT%H:%M:%S%z'
                ).replace(tzinfo=None)

                if start_current_month <= bill_date <= now:
                    print(f"{get_current_time()}: Downloading bill: {bill_id} for account {account['application_key']}")

                    pdf_url = bill_details.get('pdfUrl')
                    if not pdf_url:
                        print(f"{get_current_time()}: No pdfUrl found for bill {bill_id}")
                        continue

                    pdf_path = os.path.join(account["bills_folder"], f"{bill_id}.pdf")

                    try:
                        download_pdf_with_retry(
                            pdf_url=pdf_url,
                            pdf_path=pdf_path,
                            max_attempts=10,
                            wait_seconds=15
                        )
                        all_pdf_paths.append(pdf_path)
                        sent_bills.add(bill_id)

                    except Exception as e:
                        print(f"{get_current_time()}: Failed to download valid PDF for bill {bill_id}: {e}")

            update_sent_bills(sent_bills_file_path, sent_bills)

        except Exception as e:
            print(f"{get_current_time()}: Error processing account {account['application_key']}: {e}")

    return all_pdf_paths


# Send mail with pdfs
def send_mail_with_pdfs(pdf_paths, mail_recipient, smtp_server):
    if not pdf_paths:
        print(f"{get_current_time()}: No new bills to send.")
        return False

    msg = MIMEMultipart()
    msg['From'] = "mail@domain.com"
    msg['To'] = mail_recipient
    msg['Subject'] = "New OVH bill(s)"
    msg.attach(MIMEText(
        "Please find in attachment your/yours new OVH bill(s). "
        "Do not reply, sending mail address is not able to receive mails.",
        'plain'
    ))

    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        piece = MIMEBase('application', "octet-stream")
        with open(pdf_path, "rb") as file:
            piece.set_payload(file.read())
        encoders.encode_base64(piece)
        piece.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(piece)

    server = smtplib.SMTP(smtp_server, 25)
    server.sendmail(msg['From'], mail_recipient, msg.as_string())
    server.quit()

    print(f"{get_current_time()}: Bills sent to {mail_recipient}.")
    return True


# Main execution
pdf_paths = collect_pdf_paths(accounts)
send_mail_with_pdfs(pdf_paths, mail_recipient, smtp_server)
