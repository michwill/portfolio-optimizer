#!/usr/bin/env python3
import json
import numpy as np
from scipy.interpolate import interp1d
from scipy import optimize
from random import random

currencies = ['bitcoin', 'litecoin', 'ethereum', 'dash', 'waves']
base_currency = 'bitcoin'
data = {}
max_all = 0
min_all = 0
steps = 1000
hodl_time = 3


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
        if not max_all:
            max_all = int(data[currency][:, 0].max())
        else:
            max_all = int(min(data[currency][:, 0].max(), max_all))
        min_all = int(max(data[currency][:, 0].min(), min_all))


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

    def f(t, **currencies2):
        out = None
        for cur in currencies:
            val = abs(currencies2.get(cur, currencies[cur]))
            if out is None:
                out = splines[cur](t) * val
            else:
                out += splines[cur](t) * val
        return out

    return f


def logdrop(f, start, stop, **currencies):
    """
    Calculates sum(log(price) * t, t>=current) drop of the price in future
    Optimum portfolio should minimize this drop
    """
    times = np.linspace(start, stop, steps)
    prices = f(times, **currencies)
    prices = np.log(prices)

    drop = 0.0
    ctr = 0
    for i in range(len(prices) - 2):
        if times[-1] - times[i + 1] < hodl_time * 86400:
            break
        diffs = prices[i + 1:] - prices[i]
        diffs = diffs[times[i + 1:] - times[i] > hodl_time * 86400]
        drop += (diffs < 0).mean()
        ctr += 1

    if random() < 0.01:
        print(drop / ctr, currencies)

    return drop / ctr


def fit(start, stop):
    depo = 1000.0
    # Start with equal portfolio
    cc = {cur: depo / len(currencies) / data[cur][-1, 1]
          for cur in currencies}
    f = price_func(start - 86400 // 2, stop + 86400 // 2, **cc)
    # We'll optimize all but bitcoin (assume that Bitcoin should always be
    # present)
    pnames = [cur for cur in currencies if cur != base_currency]
    params = np.array([cc[cur] for cur in pnames])

    def target(p):
        pp = dict(zip(pnames, p))
        pp[base_currency] = cc[base_currency]
        return logdrop(
                f, start, stop, **pp)

    opt = optimize.basinhopping(
            target, params, T=100, niter=10000,
            minimizer_kwargs=dict(method="L-BFGS-B",
                                  bounds=[[0, i * 1000] for i in params]))
#            target, params, T=100, niter=10000,
    out = dict(zip(pnames, opt['x']))
    out[base_currency] = cc[base_currency]
    return target(opt['x']), out


if __name__ == '__main__':
    read_all()
    print(fit(max_all - 86400 * 65, max_all - 86400 * 5))
