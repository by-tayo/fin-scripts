"""

Time Value of Money formulas into a python script.

Every formula for moving money across time: future value, present value,
uneven cash flows, annuities, perpetuities, and combinations of them,
as plain Python (standard library only, Python 3.8+).

Conventions
-----------
* Interest rates and growth rates are DECIMALS inside the code: 5% -> 0.05.
* Time is counted in periods: t = 0 is today, t = 1 is one period from now.
* The annuity and perpetuity shortcuts give a value ONE PERIOD BEFORE THE
  FIRST PAYMENT. If the first payment is at t, the shortcut's answer is the
  value at t - 1, and it still has to be discounted back to today.

Run it
------
    python time_value.py

That prints every worked example and checks each shortcut against the
long way (adding up each payment one by one). If any check fails, the
script stops with an error instead of printing a wrong number.

For learning only. Not financial advice.
"""

from math import isclose

TOL = 1e-9


# Input checks


def _check_rate(r, name="Interest rate"):
    if r <= -1:
        raise ValueError(f"{name} must be greater than -100%")


def _check_periods(n, name="Number of periods"):
    if n < 0:
        raise ValueError(f"{name} can't be negative")


# 1. One amount: future value and present value


def future_value(amount, rate, periods):
    """FV = C x (1 + r)^n : what an amount grows to after n periods."""
    _check_rate(rate)
    _check_periods(periods)
    return amount * (1 + rate) ** periods


def present_value(amount, rate, periods):
    """PV = C / (1 + r)^n : what a future amount is worth n periods earlier."""
    _check_rate(rate)
    _check_periods(periods)
    return amount / (1 + rate) ** periods


def interest_breakdown(principal, rate, periods):
    """
    Splits the interest earned into:
      simple interest   = interest on the original amount only
      interest on interest = total interest - simple interest
    """
    fv = future_value(principal, rate, periods)
    total = fv - principal
    simple = principal * rate * periods
    return {"future_value": fv, "total_interest": total,
            "simple_interest": simple, "interest_on_interest": total - simple}


def move(amount, rate, from_period, to_period):
    """
    Move an amount from one point in time to another.
    Forward in time = compound; backward in time = discount.
    """
    gap = to_period - from_period
    _check_rate(rate)
    return amount * (1 + rate) ** gap


# 2. Several cash flows: add up each one's value


def pv_cash_flows(flows, rate, at_period=0):
    """
    Value of a list of cash flows at one point in time (today by default).
    `flows` is a list of (period, amount) pairs, e.g. [(1, 100), (2, 200)].
    """
    return sum(move(amount, rate, t, at_period) for t, amount in flows)


def timeline(flows, width=6):
    """Text drawing of a list of (period, amount) cash flows."""
    if not flows:
        return "(no cash flows)"
    last = max(t for t, _ in flows)
    by_t = {}
    for t, a in flows:
        by_t[t] = by_t.get(t, 0) + a
    top = "".join(f"{t:^{width + 4}}" for t in range(0, int(last) + 1))
    line = "".join("|" + "-" * (width + 3) for _ in range(0, int(last) + 1))
    vals = "".join(f"{(f'{by_t[t]:,.0f}' if t in by_t else ''):^{width + 4}}"
                   for t in range(0, int(last) + 1))
    return f"  Period: {top}\n          {line}\n  Cash:   {vals}"


# 3. Shortcuts for patterns (value is one period BEFORE the first payment)


def pv_annuity(payment, rate, n_payments):
    """Constant annuity: PV = C / r x [1 - 1 / (1 + r)^N]."""
    _check_rate(rate)
    _check_periods(n_payments, "Number of payments")
    if rate == 0:
        return payment * n_payments
    return payment / rate * (1 - 1 / (1 + rate) ** n_payments)


def pv_growing_annuity(first_payment, rate, growth, n_payments):
    """Growing annuity: PV = C / (r - g) x [1 - ((1 + g) / (1 + r))^N]."""
    _check_rate(rate)
    _check_rate(growth, "Growth rate")
    _check_periods(n_payments, "Number of payments")
    if isclose(rate, growth):
        # When r = g every payment is worth the same today: C / (1 + r) each
        return first_payment * n_payments / (1 + rate)
    return first_payment / (rate - growth) * (1 - ((1 + growth) / (1 + rate)) ** n_payments)


def pv_perpetuity(payment, rate):
    """Constant perpetuity: PV = C / r."""
    if rate <= 0:
        raise ValueError("A perpetuity needs an interest rate above 0%")
    return payment / rate


def pv_growing_perpetuity(first_payment, rate, growth):
    """Growing perpetuity: PV = C / (r - g). Only works when g < r."""
    if growth >= rate:
        raise ValueError("Growth rate must be lower than the interest rate, "
                         "or the value would be infinite")
    _check_rate(growth, "Growth rate")
    return first_payment / (rate - growth)


def value_today(value_one_period_before_first, first_payment_period, rate):
    """
    The shortcuts give a value at (first payment period - 1).
    Discount that back to today (period 0).
    """
    return move(value_one_period_before_first, rate, first_payment_period - 1, 0)


def pattern_cash_flows(payment, n_payments, first_period=1, growth=0.0):
    """List the individual payments of an annuity, so you can check the long way."""
    return [(first_period + k, payment * (1 + growth) ** k) for k in range(n_payments)]


# Worked examples (all numbers made up)


def worked_examples():
    ex = {}

    # 1. $1,000 at 5% for 3 years
    ex["ib"] = interest_breakdown(1000, 0.05, 3)
    ex["pv1"] = present_value(1000, 0.05, 3)
    assert isclose(present_value(ex["ib"]["future_value"], 0.05, 3), 1000), "FV and PV must undo each other"
    assert isclose(move(1000, 0.05, 3, 0), ex["pv1"]) and isclose(move(1000, 0.05, 0, 3), ex["ib"]["future_value"])

    # 2. Uneven cash flows: $100, $200, $300 in years 1-3 at 5%
    ex["flows"] = [(1, 100), (2, 200), (3, 300)]
    ex["each"] = [present_value(a, 0.05, t) for t, a in ex["flows"]]
    ex["pv_flows"] = pv_cash_flows(ex["flows"], 0.05)
    assert isclose(ex["pv_flows"], sum(ex["each"]))

    # 3. Shortcuts, each checked against adding up every payment
    ex["ann"] = pv_annuity(1000, 0.06, 5)
    assert isclose(ex["ann"], pv_cash_flows(pattern_cash_flows(1000, 5), 0.06)), "Annuity shortcut must match the long way"

    ex["gann"] = pv_growing_annuity(1000, 0.06, 0.03, 5)
    assert isclose(ex["gann"], pv_cash_flows(pattern_cash_flows(1000, 5, growth=0.03), 0.06)), "Growing annuity must match"

    ex["perp"] = pv_perpetuity(1000, 0.05)
    assert abs(ex["perp"] - pv_annuity(1000, 0.05, 2000)) < 1e-6, "Perpetuity = very long annuity"

    ex["gperp"] = pv_growing_perpetuity(1000, 0.06, 0.03)
    assert abs(ex["gperp"] - pv_growing_annuity(1000, 0.06, 0.03, 5000)) < 1e-4, "Growing perpetuity = very long growing annuity"

    # 3b. Deferred annuity: 4 payments of $1,000 starting in year 3, at 6%
    ex["def_at2"] = pv_annuity(1000, 0.06, 4)
    ex["def_today"] = value_today(ex["def_at2"], 3, 0.06)
    assert isclose(ex["def_today"], pv_cash_flows(pattern_cash_flows(1000, 4, first_period=3), 0.06)), "Deferred annuity must match"

    # 4. Combination: $1,000 a year for years 1-5, then $1,500 a year forever from year 6, at 6%
    part1 = pv_annuity(1000, 0.06, 5)
    part2_at5 = pv_perpetuity(1500, 0.06)
    part2 = value_today(part2_at5, 6, 0.06)
    ex["combo"] = dict(part1=part1, part2_at5=part2_at5, part2=part2, total=part1 + part2)
    long_way = pv_cash_flows(pattern_cash_flows(1000, 5) + pattern_cash_flows(1500, 3000, first_period=6), 0.06)
    assert abs(ex["combo"]["total"] - long_way) < 1e-6, "Combination must match the long way"
    return ex


def money(x):
    return f"${x:,.2f}"


def main():
    ex = worked_examples()
    ib = ex["ib"]
    print("1. ONE AMOUNT ($1,000 at 5% for 3 years)")
    print(f"   Future value {money(ib['future_value'])}: total interest {money(ib['total_interest'])} = "
          f"simple {money(ib['simple_interest'])} + interest on interest {money(ib['interest_on_interest'])}")
    print(f"   $1,000 received in 3 years is worth {money(ex['pv1'])} today")

    print("\n2. UNEVEN CASH FLOWS ($100, $200, $300 in years 1-3 at 5%)")
    print(timeline(ex["flows"]))
    print("   " + " + ".join(money(v) for v in ex["each"]) + f" = {money(ex['pv_flows'])}")

    print("\n3. SHORTCUTS (value one period before the first payment)")
    print(f"   Annuity: $1,000 a year for 5 years at 6%            -> {money(ex['ann'])}")
    print(f"   Growing annuity: $1,000 growing 3%, 5 years, at 6%   -> {money(ex['gann'])}")
    print(f"   Perpetuity: $1,000 a year forever at 5%              -> {money(ex['perp'])}")
    print(f"   Growing perpetuity: $1,000 growing 3% forever, at 6% -> {money(ex['gperp'])}")
    print(f"   Deferred: 4 x $1,000 starting year 3 at 6%: {money(ex['def_at2'])} at year 2 "
          f"-> {money(ex['def_today'])} today")

    c = ex["combo"]
    print("\n4. COMBINATION ($1,000/yr for years 1-5, then $1,500/yr forever from year 6, at 6%)")
    print(f"   Annuity part today {money(c['part1'])} + perpetuity part {money(c['part2_at5'])} at year 5 "
          f"-> {money(c['part2'])} today = {money(c['total'])}")
    print("\nAll cross-checks passed.")


if __name__ == "__main__":
    main()
