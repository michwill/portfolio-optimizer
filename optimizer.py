#!/usr/bin/env python3
import json
import numpy as np
from scipy.interpolate import interp1d

currencies = ['bitcoin', 'litecoin', 'ethereum', 'dash', 'waves']
data = {}
max_all = 0
min_all = 0


def read(currency):
    with open('data/%s.json' % currency) as f:
        arr = np.array(json.load(f))
        arr[:, 0] /= 1000
        return arr


def read_all():
    global max_all
    global min_all

    for currency in currencies:
        data[currency] = read(currency)
        max_all = int(max(data[currency][:, 0].max(), max_all))
        if not min_all:
            min_all = max_all
        min_all = int(min(data[currency][:, 0].min(), min_all))


def slice(start, stop):
    out_data = {}
    for currency in currencies:
        times = data[currency][:, 0]
        out_data[currency] = data[currency][(times >= start) * (times < stop)]
    return out_data


def price_func(start, stop, **currencies):
    splines = {}
    for cur, val in currencies.items():
        times = data[cur][:, 0]
        splines[cur] = interp1d(
                times[(times >= start) * (times < stop)],
                data[cur][(times >= start) * (times < stop)][:, 1],
                kind='cubic')

    def f(t):
        out = None
        for cur, val in currencies.items():
            if not out:
                out = splines[cur](t) * val
            else:
                out += splines[cur](t) * val
        return out

    return f


if __name__ == '__main__':
    read_all()
    f = price_func(max_all - 30 * 86400 * 2, max_all,
                   bitcoin=1, litecoin=1, dash=1,
                   ethereum=1, waves=1)
    import IPython
    IPython.embed()
