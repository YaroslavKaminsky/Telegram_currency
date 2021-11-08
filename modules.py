import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta


def rounded(number: float, precision: int):
    number = int(number * 10 ** (precision+1))
    if number % 10 < 5:
        result = int(number / 10) / (10 ** precision)
    else:
        result = (int(number / 10) + 1) / (10 ** precision)
    return result


def format_time_series(request_data):
    base = request_data['base']
    dates = list(request_data['rates'].keys())
    raw_values = list(request_data['rates'].values())
    currencies = {}
    for key in raw_values[0].keys():
        currencies[key] = []
    for item in raw_values:
        for key, value in item.items():
            currencies[key].append(rounded(value, 2))
    return dates, currencies, base


def rate_history(dates: list, currencies, base='USD'):
    pass
    # for currency, values in currencies.items():
    #     plt.plot(dates, values, label=currency)
    # plt.xlabel('date')
    # plt.ylabel(f'value({base})')
    # plt.title(f'Rate history from {dates[0]} to {dates[-1]}')
    # plt.savefig(r'static\img')


if __name__ == "__main__":
#     mock = {
#     "disclaimer": "https://openexchangerates.org/terms/",
#     "license": "https://openexchangerates.org/license/",
#     "start_date": "2013-01-01",
#     "end_date": "2013-01-31",
#     "base": "AUD",
#     "rates": {
#         "2013-01-01": {
#             # "BTC": 0.0778595876,
#             # "EUR": 0.785518,
#             "HKD": 8.04136
#         },
#         "2013-01-02": {
#             # "BTC": 0.0789400739,
#             # "EUR": 0.795034,
#             "HKD": 8.138096
#         },
#         "2013-01-03": {
#             # "BTC": 0.0785299961,
#             # "EUR": 0.80092,
#             "HKD": 8.116954
#         },
#     }
# }
# dates, currencies, base = format_time_series(mock)
# rate_history(dates, currencies, base)
    print((datetime.now() - datetime.fromtimestamp(1449877801)).total_seconds())

