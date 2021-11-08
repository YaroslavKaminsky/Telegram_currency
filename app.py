from flask import Flask, request, render_template
import re
from flask_sqlalchemy import SQLAlchemy
import os
import modules
import requests
from datetime import datetime, date

app = Flask(__name__)

ENV = 'dev'
TELEGRAM_BOT_API = os.environ.get('TELEGRAM_API')
CURRENCY_RATES_API = os.environ.get('CURRENCY_API')
API_ENDPOINT = 'https://openexchangerates.org/api/'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Currencies(db.Model):
    __tablename__ = 'currencies_data'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(3), unique=True)
    value = db.Column(db.Float)
    time_stamp = db.Column(db.Integer)

    def __init__(self, name, value, time_stamp):
        self.name = name
        self.value = value
        self.time_stamp = time_stamp


class Log_operations(db.Model):
    __tablename__ = 'operations'

    id = db.Column(db.Integer, primary_key=True)
    operation = db.Column(db.String(200))
    operation_time = db.Column(db.String(25))

    def __init__(self, operation, operation_time):
        self.operation = operation
        self.operation_time = operation_time


class Log_errors(db.Model):
    __tablename__ = 'errors'

    id = db.Column(db.Integer, primary_key=True)
    error = db.Column(db.String(200))
    error_time = db.Column(db.String(25))

    def __init__(self, error, error_time):
        self.error = error
        self.error_time = error_time


def log_writer(log, log_type='operation'):
    if log_type == 'operation':
        new_log = Log_operations(operation=log, operation_time=datetime.now().strftime('%d-%m-%Y %H:%M'))
        db.session.add(new_log)
        db.session.commit()
    elif log_type == 'error':
        new_log = Log_errors(error=log, error_time=datetime.now().strftime('%d-%m-%Y %H:%M'))
        db.session.add(new_log)
        db.session.commit()


def check_empty():
    db_result = db.session.query(Currencies.time_stamp).filter(Currencies.id > 0).first()
    return db_result is None


def check_timedelta():
    db_time = db.session.query(Currencies.time_stamp).first()[0]
    time_delta = (datetime.now()-datetime.fromtimestamp(db_time)).total_seconds()
    return time_delta > 3600


def check_currency(name):
    db_result = db.session.query(Currencies).filter(Currencies.name == name).count()
    return db_result != 0


def get_all_rates():
    access_key = 'app_id=' + CURRENCY_RATES_API
    end_point = API_ENDPOINT + 'latest.json'
    url = f"{end_point}?{access_key}"
    print(url)
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if 'error' in response.json():
        message = response.json()['message']
        log_writer(message, 'error')
        return response.json()['description']
    else:
        print('rates were got')
        print(response.json()['rates'], response.json()['timestamp'])
        return response.json()['rates'], response.json()['timestamp']


def update_currencies():
    if check_empty() or check_timedelta():
        response = get_all_rates()
        if len(response) == 2:
            currency_rates, time_stamp = response
            for name, value in currency_rates.items():
                if check_currency(name):
                    db_data = {
                        'value': modules.rounded(value, 2),
                        'time_stamp': time_stamp
                    }
                    db.session.query(Currencies).filter(Currencies.name == name).update(db_data)
                else:
                    data = Currencies(name=name, value=modules.rounded(value, 2), time_stamp=time_stamp)
                    db.session.add(data)
            db.session.commit()
            log_writer('db is updated')
            return True
        else:
            return response
    return True


def get_rates_list(command_line):
    result = []
    command = command_line.split(' ')
    if len(command) == 1:
        symbols = {'AUD', 'CAD', 'CHF', 'CHK', 'CNY', 'EUR', 'PLN', 'RUB', 'UAH'}
    else:
        symbols = set()
        pattern = r"[A-Z]{3}"
        for symbol in command[1:]:
            new_symbols = set(re.findall(pattern, symbol.upper()))
            symbols.update(new_symbols)
    db_data = db.session.query(Currencies.name, Currencies.value).filter(Currencies.name.in_(symbols)).all()
    for row in db_data:
        result.append(f'{row[0]}: {row[1]}\n')
        log_writer('get rates list')
    return ''.join(result), None


def get_currency_value(name):
    result = db.session.query(Currencies.value).filter(Currencies.name == name).first()[0]
    return result


def exchange(command_line):
    pattern = r"(^/exchange\s+\$[0-9]+.+[A-Z]{3}$)|(^/exchange\s+[0-9]+\sUSD.+[A-Z]{3}$)"
    if re.match(pattern, command_line):
        quantity = re.findall(r'[0-9]+', command_line)[0]
        name = re.findall(r'[A-Z]{3}$', command_line)[0]
        value = get_currency_value(name)
        result = f'{value * int(quantity)}{name}\n'
    else:
        result = "Incorrect pattern. Please use example:'/exchange $10 to CAD'"
    log_writer('get exchange')
    return result, None


def start(command_line):
    print(command_line)
    return 'Welcome', None


def send_message(chat_id, text):
    method = "sendMessage"
    token = TELEGRAM_BOT_API
    url = f'https://api.telegram.org/bot{token}/{method}'
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)
    log_writer(f'Send message to chat_id:{chat_id}')


def send_photo(chat_id, photo=r'static\img.png'):
    method = "sendPhoto"
    token = TELEGRAM_BOT_API
    url = f'https://api.telegram.org/bot{token}/{method}'
    data = {"chat_id": chat_id, "photo": open(photo, 'rb')}
    requests.post(url, data=data)
    log_writer(f'Send photo to chat_id:{chat_id}')


def get_history(start, end, symbols, base='USD'):
    mock = {
    "disclaimer": "https://openexchangerates.org/terms/",
    "license": "https://openexchangerates.org/license/",
    "start_date": "2013-01-01",
    "end_date": "2013-01-31",
    "base": "AUD",
    "rates": {
        "2013-01-01": {
            # "BTC": 0.0778595876,
            # "EUR": 0.785518,
            "HKD": 8.04136
        },
        "2013-01-02": {
            # "BTC": 0.0789400739,
            # "EUR": 0.795034,
            "HKD": 8.138096
        },
        "2013-01-03": {
            # "BTC": 0.0785299961,
            # "EUR": 0.80092,
            "HKD": 8.116954
        },
    }
}
    result = []
    access_key = 'app_id=' + CURRENCY_RATES_API
    end_point = API_ENDPOINT + 'time-series.json'
    url = f"{end_point}?{access_key}"
    print(url)
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if 'error' in response.json():
        message = response.json()['message']
        log_writer(message, 'error')
        result.append(mock)
        result.append(response.json()['description'])
        return result
    else:
        result.append(response.json())
        result.append('OK')
        return result
    pass


def history_demo(command_line):
    pattern = r"^/history\s+([12][0-9]{3}-[01][0-9]-[0123][0-9]\s+){2}([a-zA-Z]{3})+"
    print(re.match(pattern, command_line))
    if re.match(pattern, command_line):
        command = command_line.split(' ')
        try:
            print(datetime.strptime(command[1], '%Y-%m-%d'))
            print(datetime.strptime(command[2], '%Y-%m-%d'))
        except ValueError:
            message = 'Incorrect date format'
            return message, None
        symbols_raw = ' '.join(command[3:])
        print(symbols_raw)
        symbols_list = re.findall(r'[A-Z]{3}', symbols_raw.upper())
        print(symbols_list)
        symbols = ','.join(symbols_list)
        print(symbols)
        if command[1] < command[2]:
            start, end = command[1], command[2]
        else:
            start, end = command[2], command[1]
        request_data, message = get_history(start, end, symbols)
        dates, currencies, base = modules.format_time_series(request_data)
        modules.rate_history(dates, currencies, base)
        return message, r'static/img.png'
    else:
        message = "Incorrect pattern. Please use example:'/history 2020-12-13 2020-12-19 UAH'"
        return message, None


commands = {
    '/list': get_rates_list,
    '/lst': get_rates_list,
    '/exchange': exchange,
    '/start': start,
    '/history': history_demo
}


@app.route('/', methods=['POST'])
def process():
    message_info = request.json.get('message', request.json.get('edited_message', {}))
    command_line = message_info.get('text')
    command_line = command_line.strip()
    command = command_line.split(' ')
    if command[0] in commands:
        update_currencies()
        result = commands[command[0]](command_line)
    else:
        result = ('There is no such command.', None)

    chat_id = request.json['message']['chat']['id']
    print(chat_id)
    send_message(chat_id=chat_id, text=result[0])
    if result[1] is not None:
        try:
            send_photo(chat_id=chat_id)
        except RuntimeError:
            send_message(chat_id=chat_id, text='Cannot send you a plot')
    return "True"


@app.route('/logs')
def data_table():
    data_log = db.session.query(Log_operations).all()
    return render_template('database_table.html',data_log=data_log)


if __name__ == '__main__':
    app.run()
    # method = "sendPhoto"
    # token = TELEGRAM_BOT_API
    # url = f'https://api.telegram.org/bot{token}/{method}'
    # data = {"chat_id": 643575590, "photo": open('static/img.png', 'rb')}
    #
    # requests.post(url, data=data)

