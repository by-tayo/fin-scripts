"""

Risk and Return formulas into a python script.

Every formula from the risk-and-return formula guide, as plain Python
(standard library only, Python 3.8+).

Conventions
-----------
* Returns, standard deviations and weights are DECIMALS: 10% -> 0.10.
* Variances are in decimal-squared units (0.10 ** 2 = 0.01).
  Multiply by 10,000 to get "percent-squared" (0.01 -> 100 %^2).
* History-based variance and covariance divide by (T - 1), the
  sample convention.

Run it
------
    python risk_return.py

That prints every worked example from the guide and runs the
cross-checks (two methods that must agree, risk contributions that
must add up, and so on). If any check fails, the script stops with
an error instead of printing a wrong number.
"""

from math import sqrt, isclose

TOL = 1e-9


# Input checks


def _check_same_length(*seqs):
    lengths = {len(s) for s in seqs}
    if len(lengths) != 1:
        raise ValueError(f"Inputs must be the same length, got lengths {sorted(lengths)}")


def _check_sums_to_one(values, name):
    total = sum(values)
    if not isclose(total, 1.0, abs_tol=1e-6):
        raise ValueError(f"{name} must add up to 1 (100%), got {total:.6f}")


def _check_min_periods(returns, minimum=2):
    if len(returns) < minimum:
        raise ValueError(f"Need at least {minimum} periods of returns, got {len(returns)}")


# 1. Return on one investment over one period


def market_value(units, price_per_unit):
    """Market value = number of units x price per unit."""
    return units * price_per_unit


def capital_gain(mv_begin, mv_end):
    """Capital gain (loss) = value at end - value at beginning."""
    return mv_end - mv_begin


def total_profit(mv_begin, mv_end, income=0.0):
    """Total profit = value at end - value at beginning + income received."""
    return mv_end - mv_begin + income


def asset_return(price_begin, price_end, income=0.0):
    """
    Return over one period, split into its two sources.

    total return       = (P_end - P_begin + C) / P_begin
    capital gain yield = (P_end - P_begin) / P_begin
    income yield       = C / P_begin   (the dividend yield, for a stock)
    """
    if price_begin <= 0:
        raise ValueError("Beginning price must be positive")
    cg_yield = (price_end - price_begin) / price_begin
    inc_yield = income / price_begin
    return {"total": cg_yield + inc_yield,
            "capital_gain_yield": cg_yield,
            "income_yield": inc_yield}


def return_after_share_change(value_at_end_of_one_original_share,
                              price_begin, dividends_received=0.0):
    """
    Return when the share changes shape during the period (a spin-off or
    a stock split). Follow ONE share you bought at the start:

        return = (value at end of everything that one share became
                  - price paid for it
                  + all dividends received on it) / price paid for it
    """
    if price_begin <= 0:
        raise ValueError("Beginning price must be positive")
    return (value_at_end_of_one_original_share - price_begin
            + dividends_received) / price_begin


def profit_from_return(period_return, amount_invested):
    """Total profit (loss) = return x amount invested."""
    return period_return * amount_invested


# 2. Expected return and risk when the possible outcomes are known


def expected_return(probabilities, returns):
    """E(R) = sum of (probability of each scenario x return in that scenario)."""
    _check_same_length(probabilities, returns)
    _check_sums_to_one(probabilities, "Probabilities")
    return sum(p * r for p, r in zip(probabilities, returns))


def scenario_variance(probabilities, returns):
    """Variance = sum of probability x (return - expected return) squared."""
    er = expected_return(probabilities, returns)
    return sum(p * (r - er) ** 2 for p, r in zip(probabilities, returns))


def scenario_sd(probabilities, returns):
    """Standard deviation (risk) = square root of the variance."""
    return sqrt(scenario_variance(probabilities, returns))


# 3. Average return and risk from past returns


def average_return(returns):
    """Arithmetic average = (R1 + R2 + ... + RT) / T."""
    _check_min_periods(returns, 1)
    return sum(returns) / len(returns)


def historical_variance(returns):
    """Variance = sum of (return - average) squared, divided by (T - 1)."""
    _check_min_periods(returns, 2)
    avg = average_return(returns)
    return sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)


def historical_sd(returns):
    """Standard deviation (risk) = square root of the variance."""
    return sqrt(historical_variance(returns))


# 4. Portfolio return

def weights_from_values(market_values):
    """Weight of each holding = its market value / value of the whole portfolio."""
    total = sum(market_values)
    if total <= 0:
        raise ValueError("Total portfolio value must be positive")
    return [mv / total for mv in market_values]


def portfolio_return(weights, returns):
    """R_p = w1*R1 + w2*R2 + ... + wn*Rn."""
    _check_same_length(weights, returns)
    _check_sums_to_one(weights, "Weights")
    return sum(w * r for w, r in zip(weights, returns))


def portfolio_return_by_dollars(mv_begin_list, mv_end_list, income_list):
    """Method 1: add up every dollar of profit, divide by dollars invested."""
    _check_same_length(mv_begin_list, mv_end_list, income_list)
    profit = sum(total_profit(b, e, c)
                 for b, e, c in zip(mv_begin_list, mv_end_list, income_list))
    return profit / sum(mv_begin_list)


# 5. Expected return of a portfolio


def portfolio_expected_return(weights, expected_returns):
    """E(R_p) = w1*E(R1) + w2*E(R2) + ... + wn*E(Rn)."""
    return portfolio_return(weights, expected_returns)



# 6. Correlation and portfolio risk


def historical_covariance(returns_a, returns_b):
    """
    Covariance from past returns (sample convention):
    sum of (A's gap from its average x B's gap from its average) / (T - 1).
    """
    _check_same_length(returns_a, returns_b)
    _check_min_periods(returns_a, 2)
    avg_a, avg_b = average_return(returns_a), average_return(returns_b)
    return (sum((a - avg_a) * (b - avg_b) for a, b in zip(returns_a, returns_b))
            / (len(returns_a) - 1))


def correlation_from_cov(cov_ab, sd_a, sd_b):
    """Corr(A, B) = Cov(A, B) / (sd_A x sd_B). Always between -1 and +1."""
    if sd_a == 0 or sd_b == 0:
        raise ValueError("Correlation is undefined when a standard deviation is 0")
    return cov_ab / (sd_a * sd_b)


def historical_correlation(returns_a, returns_b):
    """Correlation computed straight from two series of past returns."""
    return correlation_from_cov(historical_covariance(returns_a, returns_b),
                                historical_sd(returns_a), historical_sd(returns_b))


def portfolio_variance_two(w_a, w_b, sd_a, sd_b, corr_ab):
    """sigma_p^2 = wA^2 sdA^2 + wB^2 sdB^2 + 2 wA wB corrAB sdA sdB."""
    _check_sums_to_one([w_a, w_b], "Weights")
    return (w_a ** 2 * sd_a ** 2 + w_b ** 2 * sd_b ** 2
            + 2 * w_a * w_b * corr_ab * sd_a * sd_b)


def portfolio_variance(weights, sds, corr):
    """
    Any number of assets: one squared term per asset, plus
    2 x wi x wj x corr_ij x sd_i x sd_j for every pair.
    `corr` is a full correlation matrix (list of lists, 1s on the diagonal).
    With 3 assets this is exactly the 3-asset formula.
    """
    n = len(weights)
    _check_same_length(weights, sds, corr)
    _check_sums_to_one(weights, "Weights")
    for row in corr:
        if len(row) != n:
            raise ValueError("Correlation matrix must be n x n")
    total = 0.0
    for i in range(n):
        total += weights[i] ** 2 * sds[i] ** 2
        for j in range(i + 1, n):
            if not isclose(corr[i][j], corr[j][i]):
                raise ValueError("Correlation matrix must be symmetric")
            total += 2 * weights[i] * weights[j] * corr[i][j] * sds[i] * sds[j]
    return total


def portfolio_sd(variance):
    """sigma_p = square root of the portfolio variance."""
    if variance < -TOL:
        raise ValueError("Variance cannot be negative; check the inputs")
    return sqrt(max(variance, 0.0))


def is_diversified(portfolio_sd_value, weights, sds):
    """
    Diversification test: the portfolio is diversified when its risk is
    LOWER than the weighted average of its holdings' risks.
    Returns (diversified?, weighted average risk).
    """
    weighted_avg = sum(w * s for w, s in zip(weights, sds))
    return portfolio_sd_value < weighted_avg - TOL, weighted_avg


# 7. Relevant risk: the risk a holding actually adds to a portfolio


def relevant_risk(sd_i, corr_i_p):
    """Relevant risk of asset i = sd_i x Corr(asset i, portfolio)."""
    return sd_i * corr_i_p


def portfolio_sd_from_contributions(weights, sds, corrs_with_portfolio):
    """sigma_p = sum of wi x sd_i x Corr(asset i, portfolio)."""
    _check_same_length(weights, sds, corrs_with_portfolio)
    return sum(w * relevant_risk(s, c)
               for w, s, c in zip(weights, sds, corrs_with_portfolio))



# Worked examples (the same numbers used in the guide)


def worked_examples():
    ex = {}

    # 1. One share: bought at $40, now $43, paid a $1.20 dividend; $2,000 invested
    r = asset_return(40, 43, 1.20)
    shares = 2000 / 40
    ex["single"] = dict(p0=40, p1=43, div=1.20, invested=2000, shares=shares,
                        mv0=market_value(shares, 40), mv1=market_value(shares, 43),
                        income=shares * 1.20, **r,
                        profit=profit_from_return(r["total"], 2000))
    assert isclose(ex["single"]["profit"],
                   total_profit(ex["single"]["mv0"], ex["single"]["mv1"], ex["single"]["income"]))

    # 1b. Spin-off: 1 share bought at $50; each share receives 0.5 NewCo share.
    #     End: parent $46, NewCo $10, $1 dividend on the parent share.
    end_value = 46 + 0.5 * 10
    ex["spinoff"] = dict(p0=50, parent_end=46, ratio=0.5, child_end=10, div=1.0,
                         end_value=end_value,
                         total=return_after_share_change(end_value, 50, 1.0))

    # 1c. 2-for-1 split: 1 share bought at $80 becomes 2 shares worth $42 each;
    #     $0.50 dividend on each new share.
    ex["split"] = dict(p0=80, new_shares=2, p_end=42, div_per_new=0.50,
                       end_value=2 * 42, divs=2 * 0.50,
                       total=return_after_share_change(2 * 42, 80, 2 * 0.50))

    # 2. Scenarios: strong year 25% (30%), normal 10% (50%), weak -15% (20%)
    probs, rets = [0.30, 0.50, 0.20], [0.25, 0.10, -0.15]
    ex["scen"] = dict(names=["Strong year", "Normal year", "Weak year"],
                      probs=probs, rets=rets,
                      er=expected_return(probs, rets),
                      var=scenario_variance(probs, rets),
                      sd=scenario_sd(probs, rets))

    # 3. History: Stock M over five years
    m = [0.12, -0.04, 0.18, 0.07, 0.02]
    ex["hist"] = dict(rets=m, avg=average_return(m), var=historical_variance(m),
                      sd=historical_sd(m))

    # 4. Portfolio return, both methods: $10,000 split 60/40
    mv0 = [market_value(60, 100), market_value(200, 20)]
    mv1 = [market_value(60, 106), market_value(200, 19)]
    inc = [60 * 1.00, 0.0]
    w = weights_from_values(mv0)
    r_x = asset_return(100, 106, 1.00)["total"]
    r_y = asset_return(20, 19, 0.0)["total"]
    m1 = portfolio_return_by_dollars(mv0, mv1, inc)
    m2 = portfolio_return(w, [r_x, r_y])
    assert isclose(m1, m2), "Method 1 and Method 2 must agree"
    ex["port"] = dict(mv0=mv0, mv1=mv1, inc=inc, w=w, r=[r_x, r_y],
                      profit=[total_profit(a, b, c) for a, b, c in zip(mv0, mv1, inc)],
                      m1=m1, m2=m2,
                      w_end=weights_from_values([b + 0 for b in mv1]))

    # 5. Expected portfolio return: 70% in the scenario stock, 30% in a 4% bond fund
    ex["eport"] = dict(w=[0.70, 0.30], er=[ex["scen"]["er"], 0.04],
                       erp=portfolio_expected_return([0.70, 0.30], [ex["scen"]["er"], 0.04]))

    # 6. Correlation and two-stock risk: Stock M (above) and Stock N
    n = [0.04, 0.08, 0.06, 0.03, 0.04]
    cov = historical_covariance(m, n)
    sd_m, sd_n = historical_sd(m), historical_sd(n)
    corr = correlation_from_cov(cov, sd_m, sd_n)
    var_p = portfolio_variance_two(0.5, 0.5, sd_m, sd_n, corr)
    sd_p = portfolio_sd(var_p)
    p_series = [0.5 * a + 0.5 * b for a, b in zip(m, n)]
    assert isclose(var_p, historical_variance(p_series)), "Formula must match the long way"
    div, wavg = is_diversified(sd_p, [0.5, 0.5], [sd_m, sd_n])
    avg_m, avg_n = average_return(m), average_return(n)
    ex["corr"] = dict(m=m, n=n, avg_m=avg_m, avg_n=avg_n,
                      gaps_m=[a - avg_m for a in m], gaps_n=[b - avg_n for b in n],
                      products=[(a - avg_m) * (b - avg_n) for a, b in zip(m, n)],
                      cov=cov, sd_m=sd_m, sd_n=sd_n, var_n=historical_variance(n),
                      corr=corr, var_p=var_p, sd_p=sd_p, p_series=p_series,
                      diversified=div, wavg=wavg)

    # 6b. Three assets: equal thirds, each 20% risk
    w3, s3 = [1 / 3] * 3, [0.20] * 3
    c3 = [[1, 0.5, -0.2], [0.5, 1, 0.1], [-0.2, 0.1, 1]]
    v3 = portfolio_variance(w3, s3, c3)
    ex["three"] = dict(corr=c3, var=v3, sd=portfolio_sd(v3))

    # 6c. How correlation changes risk: 50/50, both 20% risk
    ex["dial"] = [(rho, portfolio_sd(portfolio_variance_two(0.5, 0.5, 0.20, 0.20, rho)))
                  for rho in [-1, -0.5, 0, 0.5, 1]]

    # 7. Relevant risk in the 50/50 M + N portfolio
    corr_mp = historical_correlation(m, p_series)
    corr_np = historical_correlation(n, p_series)
    rr_m, rr_n = relevant_risk(sd_m, corr_mp), relevant_risk(sd_n, corr_np)
    total = portfolio_sd_from_contributions([0.5, 0.5], [sd_m, sd_n], [corr_mp, corr_np])
    assert isclose(total, sd_p), "Contributions must add up to portfolio risk"
    ex["relevant"] = dict(corr_mp=corr_mp, corr_np=corr_np, rr_m=rr_m, rr_n=rr_n,
                          contrib=[0.5 * rr_m, 0.5 * rr_n], total=total)
    return ex


def pct(x, d=2):
    return f"{x * 100:.{d}f}%"


def pct2(v, d=2):
    """Variance in percent-squared."""
    return f"{v * 10000:.{d}f} %^2"


def main():
    ex = worked_examples()

    s = ex["single"]
    print("1. ONE INVESTMENT")
    print(f"   Bought at ${s['p0']}, now ${s['p1']}, dividend ${s['div']:.2f}")
    print(f"   Capital gain yield {pct(s['capital_gain_yield'])} + dividend yield "
          f"{pct(s['income_yield'])} = total return {pct(s['total'])}")
    print(f"   On ${s['invested']:,}: profit ${s['profit']:,.2f}")
    print(f"   Spin-off return: {pct(ex['spinoff']['total'])}   "
          f"2-for-1 split return: {pct(ex['split']['total'])}")

    sc = ex["scen"]
    print("\n2. SCENARIOS")
    print(f"   Expected return {pct(sc['er'])}, variance {pct2(sc['var'])}, risk {pct(sc['sd'])}")

    h = ex["hist"]
    print("\n3. HISTORY (Stock M)")
    print(f"   Average {pct(h['avg'])}, variance {pct2(h['var'])}, risk {pct(h['sd'])}")

    p = ex["port"]
    print("\n4. PORTFOLIO RETURN")
    print(f"   Weights {[round(x, 2) for x in p['w']]}, returns {[pct(x) for x in p['r']]}")
    print(f"   Method 1 (dollars) {pct(p['m1'])} = Method 2 (weights) {pct(p['m2'])}")

    print("\n5. EXPECTED PORTFOLIO RETURN")
    print(f"   {pct(ex['eport']['erp'])}")

    c = ex["corr"]
    print("\n6. CORRELATION AND PORTFOLIO RISK (50/50 M + N)")
    print(f"   Cov {pct2(c['cov'])}, risk M {pct(c['sd_m'])}, risk N {pct(c['sd_n'])}, "
          f"correlation {c['corr']:.3f}")
    print(f"   Portfolio variance {pct2(c['var_p'])}, risk {pct(c['sd_p'])} vs weighted "
          f"average {pct(c['wavg'])} -> diversified: {c['diversified']}")
    print(f"   Three equal-weight stocks: risk {pct(ex['three']['sd'])}")
    print("   Correlation dial (50/50, both 20%): "
          + ", ".join(f"{rho:+.1f} -> {pct(sd, 1)}" for rho, sd in ex["dial"]))

    r = ex["relevant"]
    print("\n7. RELEVANT RISK")
    print(f"   M: {pct(r['rr_m'])} (corr with portfolio {r['corr_mp']:.3f})")
    print(f"   N: {pct(r['rr_n'])} (corr with portfolio {r['corr_np']:.3f})")
    print(f"   Weighted sum {pct(r['total'])} = portfolio risk {pct(c['sd_p'])}")
    print("\nAll cross-checks passed.")


if __name__ == "__main__":
    main()
