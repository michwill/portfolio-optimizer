#!/usr/bin/env python3
import json
import numpy as np
from copy import copy
from scipy.interpolate import interp1d
from scipy import optimize
# from random import random

currencies = [
        'litecoin', 'ethereum', 'dash', 'waves', 'zcash']
base_currency = 'ethereum'
data = {}
max_all = 0
min_all = 0
steps = 1000
hodl_time = 3
sell_horizon = 14
days = 100


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
            val = currencies2.get(cur, currencies[cur])
            if out is None:
                out = val and val * splines[cur](t)
            else:
                out += val and val * splines[cur](t)
        return out

    return f


def logdrop(f, start, stop, **cur):
    """
    Calculates sum(log(price) * t, t>=current) drop of the price in future
    Optimum portfolio should minimize this drop
    """
    times = np.linspace(start, stop, steps)
    drop = 0.0
    ctr = 0
    zeros = {k: 0 for k in currencies}
    args = {c: copy(zeros) for c in currencies}
    for c in currencies:
        args[c][c] = 1
    cprices = {c: f(times, **kw) for c, kw in args.items()}

    for i in range(steps - 2):
        if times[-1] - times[i + 1] < sell_horizon * 86400:
            break
        prices = [1000.0 * cur[c] / cprices[c][i] * cprices[c] for c in currencies]
        prices = np.array(prices).sum(axis=0)
        prices = np.log(prices)
        diffs = prices[i + 1:] - prices[i]
        dt = times[i + 1:] - times[i]
        diffs = diffs[(dt > hodl_time * 86400) *
                      (dt < sell_horizon * 86400)]
        drop += (diffs < 0).mean()
        ctr += 1

    # print(drop / ctr, cur)

    return drop / ctr


def fit(start, stop):
    # Start with equal portfolio
    cc = {cur: 1 / len(currencies) for cur in currencies}
    f = price_func(start - 86400 // 2, stop + 86400 // 2, **cc)
    # We'll optimize all but bitcoin (assume that Bitcoin should always be
    # present)
    pnames = [cur for cur in currencies if cur != base_currency]
    params = np.array([cc[cur] for cur in pnames])

    def logger(x, f, accept):
        if f != 100:
            out = dict(zip(pnames, x))
            out[base_currency] = 1 - sum(out.values())
            print(f, out)

    def target(p):
        pp = dict(zip(pnames, p))
        pp[base_currency] = 1 - sum(pp.values())
        if pp[base_currency] < 0:
            return 100
        return logdrop(
                f, start, stop, **pp)

    opt = optimize.basinhopping(
            target, params, T=100, niter=10000, stepsize=0.5,
            callback=logger,
            minimizer_kwargs=dict(method="L-BFGS-B",
                                  bounds=[[0, 1] for i in params]))
                                  # options={'eps': 1e-5, 'ftol': 1e-6}))
#            target, params, T=100, niter=10000,
    out = dict(zip(pnames, opt['x']))
    out[base_currency] = 1 - sum(out.values())
    return target(opt['x']), out


if __name__ == '__main__':
    read_all()
    print(fit(max_all - 86400 * (days + sell_horizon), max_all - 86400 * sell_horizon))
