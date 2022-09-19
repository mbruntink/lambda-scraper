import os
import json
import requests
import csv, io
import boto3
from datetime import datetime
from dateutil.relativedelta import relativedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions

dynamodb = boto3.client('dynamodb')
dynamodb_resource = boto3.resource('dynamodb')
secretsmanager = boto3.client('secretsmanager')

SECRET_NAME = os.environ.get('SECRET_NAME', 'apn-portal')
CERT_TABLE_NAME = os.environ.get('CERT_TABLE_NAME', 'certifications')

chrome_options = ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-tools")
chrome_options.add_argument("--no-zygote")
chrome_options.add_argument("--single-process")
chrome_options.add_argument("--user-data-dir=/tmp/chromium")
chrome_options.binary_location = '/opt/chromium/chrome'
browser = webdriver.Chrome(
    executable_path='/opt/chromedriver/chromedriver',
    options=chrome_options,
    service_log_path='/tmp/chromedriver.log'
)

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def get_login_cookies(browser, username, password):
    print('Getting login cookies...')
    browser.get("https://partnercentral.awspartner.com/APNLogin")
    WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.ID, 'loginPage:loginForm:registerWhoEmailInput')))
    browser.find_element(By.CSS_SELECTOR, "[data-id='awsccc-cb-btn-accept']").click()
    username_input = browser.find_element(By.ID, "loginPage:loginForm:registerWhoEmailInput")
    password_input = browser.find_element(By.ID, "loginPage:loginForm:registerPassPasswordInput")
    username_input.send_keys(username)
    password_input.send_keys(password)
    browser.find_element(By.ID, "loginPage:loginForm:loginBtn").click()
    WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.ID, 'context + logout')))
    cookies = {}
    for cookie in browser.get_cookies():
        cookies[cookie['name']] = cookie['value']
    browser.close()
    return cookies

def get_cert_report(cookies):
    print('Fetching certification data...')
    certs = []
    i = 0
    report = requests.get("https://partnercentral.awspartner.com/PartnerCertificationDetailsExport", cookies=cookies, allow_redirects=True)
    report = csv.DictReader(io.StringIO(report.content.decode("utf-8"))) 
    for row in report:
        if row['Work Email'] == 'xxxxxx':
            row['Work Email'] = 'unknown-{}'.format(i)
            row['User Name'] = 'unknown-{}'.format(i)
            i += 1
        award_date = datetime.strptime(row['Award Date'], "%m/%d/%Y")
        expiration_date = datetime.strptime(row['Expiration Date'], '%m/%d/%Y')
        last_cert_date = expiration_date - relativedelta(years=3)

        if last_cert_date != award_date:
            row['Recertification Date'] = '{0.month}/{0.day}/{0.year}'.format(last_cert_date)
            row['Recertified'] = 'Recertified'
        else:
            row['Recertified'] = 'New'
        row['Last Certification Date'] = '{0.month}/{0.day}/{0.year}'.format(last_cert_date)
        certs.append(row)
    print('Found {} certifications...'.format(len(certs)))
    return certs

def delete_table(table_name):
    print('Removing table {}...'.format(table_name))
    try:
        table = dynamodb.delete_table(
            TableName=table_name
        )
    except dynamodb.exceptions.from_code('ResourceNotFoundException') as e:
        print("Table {} does not exist, skipping.".format(table_name))

def wait_for_table_not_exist(table_name):
    print('Wait until table {} is removed...'.format(table_name))
    waiter = dynamodb.get_waiter('table_not_exists')
    waiter.wait(
        TableName=table_name
    )

def wait_for_table_exist(table_name):
    print('Wait until table {} is created...'.format(table_name))
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(
        TableName=table_name
    )

def create_cert_table():
    table = dynamodb.create_table(
        TableName=CERT_TABLE_NAME,
        KeySchema=[{
            'AttributeName': 'Email',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'Cert',
            'KeyType': 'RANGE'
        }],
        TableClass='STANDARD_INFREQUENT_ACCESS',
        BillingMode='PAY_PER_REQUEST',
        AttributeDefinitions=[
            {
                'AttributeName': 'Email',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'Cert',
                'AttributeType': 'S'
            }],
        SSESpecification={
            'Enabled': True
        }
    )

def get_secret():
    response = secretsmanager.get_secret_value(
        SecretId=SECRET_NAME
    )
    secret = json.loads(response['SecretString'])
    return secret['Username'], secret['Password']

def save_cert_report(certs):
    print('Saving certification data...')
    table = dynamodb_resource.Table(CERT_TABLE_NAME)
    with table.batch_writer() as writer:
        for cert in certs:
            writer.put_item(
                Item={
                    'Email': cert['Work Email'],
                    'Cert': cert['Certificate Name'],
                    'AwardDate': cert['Award Date'],
                    'User': cert['User Name'],
                    'ExpirationDate': cert['Expiration Date'],
                    'Level':cert['Certificate Level'],
                    'RecertDate': cert.get('Recertification Date', ''),
                    'Recertified': cert['Recertified'],
                    'LastCertDate': cert['Last Certification Date']
                }
            )

def lambda_handler(event, context):
    # cleanup
    delete_table(CERT_TABLE_NAME)
    
    # login, get data
    username, password = get_secret()
    cookies = get_login_cookies(browser, username, password)
    certs = get_cert_report(cookies)

    # certs   
    wait_for_table_not_exist(CERT_TABLE_NAME)
    create_cert_table()
    wait_for_table_exist(CERT_TABLE_NAME)
    save_cert_report(certs)
    return('Found {} certifications...'.format(len(certs)))
