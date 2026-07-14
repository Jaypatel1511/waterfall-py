"""The period-by-period ladder engine (orchestrator).

Applies the LOCKED Waterfall Priority to each operating period:

  1. Senior fees & admin.
  2. Senior debt service (interest then scheduled principal, pari-passu pro-rata),
     shortfall covered by DSRA draw then equity cash-injection cure.
  3. Required reserve funding / replenishment (DSRA to required, then others).
  4. Mezzanine debt service.
  5. Mandatory ECF sweep — ECF is the residual after steps 1-4; leverage-banded;
     forced to 100% under a cash-trap.
  6. Permitted junior uses from retained ECF (6a capex / 6b top-ups / 6c distributions).
  7. Residual to equity (absent an active cash-trap).

Reserve releases and event proceeds are applied on the SEPARATE proceeds path
(to outstanding debt in priority, then equity — the equity leg gated under a
cash-trap while debt remains). CFADS stays operating-only; every non-CFADS
source is recorded separately in the ledger. The six validation assertions run
every period.
"""
from waterfall.data.schema import Deal
from waterfall.models import dates, tranches as tr, reserves as rv, sweep as sw, covenants as cov
from waterfall.audit.log import PeriodLedger, AuditLog, MECHANICAL_TEST_LABEL
from waterfall.audit import assertions as asrt
from waterfall.report.schema import PeriodResult, DealResult


def run(deal: Deal) -> DealResult:
    """Run the mechanical waterfall over ``deal`` and return a DealResult."""
    n = deal.num_periods
    months_per_period = dates._FREQ_MONTHS[deal.period_frequency]
    periods_per_year = 12 // months_per_period if months_per_period <= 12 else 1
    period_ends = deal.period_end_dates()

    # Build tranche states.
    senior_states = [tr.TrancheState(t, n, periods_per_year) for t in deal.senior_tranches]
    mezz_states = [tr.TrancheState(t, n, periods_per_year) for t in deal.mezz_tranches]
    debt_states = senior_states + mezz_states
    equity_principal = sum(t.principal for t in deal.equity_tranches)

    # Build reserve states.
    reserve_states = [rv.ReserveState(c) for c in deal.reserves]
    dsra_states = [r for r in reserve_states if r.reserve_type == "DSRA"]

    audit = AuditLog()
    ledgers = []
    periods = []
    capital_account = equity_principal

    def series(name):
        return getattr(deal, name) or [0.0] * n

    equity_in = series("equity_contributions")
    proceeds_in = series("event_proceeds")
    # Facilities are funded at close only in v0.x — the opening balance is the funded
    # amount. Mid-life facility draws are deferred to v0.1 and rejected at input
    # validation (schema UnsupportedFeatureError), so there is no facility-draw path
    # here and drawn cash can never reach the ECF sweep base or equity.

    for t in range(n):
        p_start = deal.operations_start_date if t == 0 else period_ends[t - 1]
        p_end = period_ends[t]
        cfads = float(deal.cfads_stream[t])
        ledger = PeriodLedger(t)
        ledger.add_source("cfads", cfads)

        # Per-tranche period bookkeeping. ``opening`` is the pre-period balance
        # (for the principal trace); ``accrual_balance`` is the balance interest
        # accrues on — equal to ``opening`` in v0.x, since facilities are funded at
        # close (opening balance) and mid-life draws are deferred to v0.1.
        opening = {s.name: s.balance for s in debt_states}
        accrual_balance = {}
        draws_t = {s.name: 0.0 for s in debt_states}
        scheduled_t = {s.name: 0.0 for s in debt_states}
        sweep_t = {s.name: 0.0 for s in debt_states}
        proceeds_t = {s.name: 0.0 for s in debt_states}
        interest_t = {}
        # Reserve bookkeeping.
        r_opening = {r.reserve_type: r.balance for r in reserve_states}
        r_funding = {r.reserve_type: 0.0 for r in reserve_states}
        r_topup = {r.reserve_type: 0.0 for r in reserve_states}
        r_draw = {r.reserve_type: 0.0 for r in reserve_states}
        r_release = {r.reserve_type: 0.0 for r in reserve_states}

        # Facilities are funded at close (opening balance); mid-life draws are
        # deferred to v0.1 and rejected at input validation. No draw enters the
        # operating pool, so ``cash`` is CFADS-origin only and the ECF sweep base
        # (derived from ``cash`` below) stays pure. The ``facility_draws`` output
        # column is 0 every period (principal trace: the draws term is 0).
        facility_draw = 0.0
        cash = cfads

        # --- Step 1: senior fees & admin -----------------------------------
        fees_due = _fees_for_period(deal, t)
        fees_paid = min(fees_due, max(cash, 0.0))
        cash -= fees_paid
        if fees_paid > 0:
            ledger.add_use("senior_fees", fees_paid)

        # --- Step 2: senior debt service (interest, then scheduled principal) ---
        senior_interest_due = {}
        for s in senior_states:
            dcf = dates.day_count_fraction(p_start, p_end, s.tranche.day_count)
            accrual_balance[s.name] = s.balance   # post-draw balance interest accrues on
            accrued = s.accrue_interest(dcf)
            senior_interest_due[s.name] = accrued
            interest_t[s.name] = accrued  # booked interest = accrued (paid in cash below)
        senior_sched_due = {s.name: s.scheduled_principal_due(t) for s in senior_states}
        senior_ds_due = sum(senior_interest_due.values()) + sum(senior_sched_due.values())

        # Cover a shortfall with DSRA draw then equity cure.
        cover_needed = senior_ds_due - cash
        cure_used = 0.0
        if cover_needed > 1e-12:
            for r in dsra_states:
                drawn = r.draw(cover_needed - _drawn_so_far(r_draw, r))
                if drawn > 0:
                    r_draw[r.reserve_type] += drawn
                    cash += drawn
                    ledger.add_source("reserve_draw", drawn)
                    audit.record(t, "dsra_draw",
                                 f"DSRA drawn {drawn:,.0f} to cover senior debt-service shortfall")
            remaining = senior_ds_due - cash
            if remaining > 1e-12 and equity_in[t] > 0:
                cure_used = min(remaining, equity_in[t])
                cash += cure_used
                ledger.add_source("equity_cure", cure_used)
                audit.record(t, "equity_cure",
                             f"equity cash-injection cure {cure_used:,.0f} applied at senior debt service")

        # Pay senior interest (pro-rata by due if constrained), then principal.
        int_paid = _pay_pro_rata(senior_interest_due, cash)
        cash -= sum(int_paid.values())
        senior_interest_paid = int_paid
        for s in senior_states:
            paid, cash, _ = s.pay_scheduled_principal(senior_sched_due[s.name], cash)
            scheduled_t[s.name] += paid
        senior_principal_paid = {s.name: scheduled_t[s.name] for s in senior_states}
        for s in senior_states:
            if senior_interest_paid[s.name] > 0:
                ledger.add_use("senior_interest", senior_interest_paid[s.name])
            if senior_principal_paid[s.name] > 0:
                ledger.add_use("senior_principal", senior_principal_paid[s.name])
        senior_shortfall = senior_ds_due - (sum(senior_interest_paid.values())
                                            + sum(senior_principal_paid.values()))
        if senior_shortfall > 1e-6:
            audit.record(t, "senior_shortfall",
                         f"senior debt-service shortfall {senior_shortfall:,.0f} — {MECHANICAL_TEST_LABEL}",
                         mechanical_test_result=True)

        # --- Step 3: required reserve funding / replenishment --------------
        for r in reserve_states:
            if not r.config.required:
                continue
            if r.reserve_type == "DSRA" and r.config.months_dsra is not None:
                r.set_required(rv.dsra_required(r.config.months_dsra, senior_ds_due,
                                                months_per_period))
            funded, cash = r.replenish(cash)
            if funded > 0:
                r_funding[r.reserve_type] += funded
                ledger.add_use("reserve_funding", funded)
                audit.record(t, "reserve_replenish",
                             f"{r.reserve_type} replenished {funded:,.0f} toward required {r.required:,.0f}")

        # --- Step 4: mezzanine debt service --------------------------------
        for s in mezz_states:
            dcf = dates.day_count_fraction(p_start, p_end, s.tranche.day_count)
            accrual_balance[s.name] = s.balance
            accrued = s.accrue_interest(dcf)
            interest_t[s.name] = accrued
            if s.tranche.pik:
                s.capitalize_pik(accrued)   # capitalized, not a cash movement
            else:
                paid = min(accrued, max(cash, 0.0))
                cash -= paid
                if paid > 0:
                    ledger.add_use("mezz_interest", paid)
            sched = s.scheduled_principal_due(t)
            paid, cash, _ = s.pay_scheduled_principal(sched, cash)
            scheduled_t[s.name] += paid
            if paid > 0:
                ledger.add_use("mezz_principal", paid)
        mezz_ds_due = _mezz_ds_due(mezz_states, interest_t, t)

        # --- Covenants + cash-trap (evaluated before the sweep) -----------
        senior_balance = sum(s.balance for s in senior_states)
        total_debt = senior_balance + sum(s.balance for s in mezz_states)
        cov_status, dscr_value = _evaluate_covenants(
            deal, t, cfads, senior_interest_due, senior_sched_due, interest_t,
            mezz_states, senior_balance, total_debt, periods_per_year, audit)
        cash_trap = any(v in ("trap", "default") for v in cov_status.values())

        # --- Step 5: mandatory ECF sweep -----------------------------------
        ecf_base = max(cash, 0.0)   # physical residual after steps 1-4 == ECF
        annualized_cfads = cfads * periods_per_year
        leverage = total_debt / annualized_cfads if annualized_cfads > 0 else float("inf")
        sweep_pct = sw.sweep_pct_for_leverage(deal.sweep, leverage)
        swept, retained = sw.apply_sweep(ecf_base, sweep_pct, cash_trap)
        swept_applied = _apply_prepayment([senior_states, mezz_states], swept, "sweep",
                                          sweep_t, proceeds_t, t)
        cash -= swept_applied
        if swept_applied > 0:
            ledger.add_use("ecf_sweep", swept_applied)
            audit.record(t, "ecf_sweep",
                         f"ECF sweep {swept_applied:,.0f} ({'100% (cash-trap)' if cash_trap else f'{sweep_pct:.0%}'})")

        # --- Steps 6-7: junior uses / residual to equity -------------------
        # 6a growth/discretionary capex is scoped out of v0.x (no growth-capex spend
        # input; documented limitation). 6b discretionary reserve top-ups and 6c
        # permitted distributions are modeled below from retained ECF.
        junior = {"growth_capex": 0.0, "reserve_topups": 0.0, "distributions": 0.0}
        equity_distribution = 0.0
        debt_outstanding = sum(s.balance for s in debt_states)
        if not cash_trap:
            # Step 6b: discretionary reserve top-ups (up to each reserve's cap).
            for r in reserve_states:
                if cash <= 1e-12:
                    break
                topped = r.discretionary_top_up(cash)
                if topped > 0:
                    r_topup[r.reserve_type] += topped
                    junior["reserve_topups"] += topped
                    cash -= topped
                    ledger.add_use("reserve_topup", topped)
                    audit.record(t, "reserve_topup",
                                 f"{r.reserve_type} discretionary top-up {topped:,.0f} (step 6b)")
            # Steps 6c/7: permitted distributions, then residual to equity.
            if cash > 1e-12:
                equity_distribution = cash
                junior["distributions"] = equity_distribution
                cash = 0.0
                ledger.add_use("equity_distribution", equity_distribution)
        elif debt_outstanding <= 1e-9 and cash > 1e-12:
            # C1: trap active but the forced 100% sweep retired ALL debt -> the trap
            # is moot (no lender left to protect); residual operating cash flows to
            # step-7 equity, mirroring the separate proceeds path (methodology
            # cash-trap paragraph + step 7). Without this the residual would be
            # neither swept (no debt) nor distributed (steps 6-7 gated under a trap
            # while debt remains), stranding cash and firing cash-conservation.
            equity_distribution = cash
            cash = 0.0
            ledger.add_use("equity_distribution", equity_distribution)

        # --- Separate proceeds path: reserve releases + event proceeds -----
        release_total = 0.0
        for r in reserve_states:
            trigger = r.config.release_period
            if trigger == t or (t == n - 1 and r.balance > 0 and trigger is None):
                released = r.release()
                if released > 0:
                    r_release[r.reserve_type] += released
                    release_total += released
                    audit.record(t, "reserve_release",
                                 f"{r.reserve_type} released {released:,.0f} to the proceeds path")
        event_proceeds = proceeds_in[t]
        proceeds_pool = release_total + event_proceeds
        if release_total > 0:
            ledger.add_source("reserve_release", release_total)
        if event_proceeds > 0:
            ledger.add_source("event_proceeds", event_proceeds)
        proceeds_to_debt = _apply_prepayment([senior_states, mezz_states], proceeds_pool,
                                             "proceeds", sweep_t, proceeds_t, t)
        if proceeds_to_debt > 0:
            ledger.add_use("proceeds_to_debt", proceeds_to_debt)
            audit.record(t, "proceeds_applied",
                         f"{proceeds_to_debt:,.0f} of reserve-release / event proceeds "
                         "applied to outstanding debt in priority order")
        proceeds_residual = proceeds_pool - proceeds_to_debt
        proceeds_to_equity = 0.0
        # Residual only exists once all debt is retired (proceeds absorbed in priority),
        # so the trap's equity gate is satisfied: it reaches equity only after payoff.
        if proceeds_residual > 1e-12:
            proceeds_to_equity = proceeds_residual
            ledger.add_use("proceeds_to_equity", proceeds_to_equity)

        # --- Assertions (six) ----------------------------------------------
        asrt.assert_cash_conservation(ledger)
        for s in debt_states:
            dcf = dates.day_count_fraction(p_start, p_end, s.tranche.day_count)
            asrt.assert_interest_reconciliation(
                s.name, t, s.tranche.coupon, accrual_balance[s.name], dcf, interest_t[s.name])
            asrt.assert_principal_trace(
                s.name, t, opening[s.name], draws_t[s.name], scheduled_t[s.name],
                proceeds_t[s.name], sweep_t[s.name], s.balance)
        for r in reserve_states:
            asrt.assert_reserve_roll_forward(
                r.reserve_type, t, r_opening[r.reserve_type], r_funding[r.reserve_type],
                r_topup[r.reserve_type], r_draw[r.reserve_type], r_release[r.reserve_type],
                r.balance)
        contributions = cure_used
        distributions = equity_distribution + proceeds_to_equity
        ending_ca = capital_account + contributions - distributions
        asrt.assert_capital_account(t, capital_account, contributions, distributions, ending_ca)
        capital_account = ending_ca

        # --- Build the period row ------------------------------------------
        ds_by_tranche = {s.name: interest_t[s.name] + scheduled_t[s.name] for s in debt_states}
        periods.append(PeriodResult(
            period_index=t, period_end_date=p_end, cfads=cfads, fees=fees_paid,
            facility_draws=facility_draw, equity_contributions=cure_used,
            debt_service_by_tranche=ds_by_tranche,
            principal_by_tranche={s.name: scheduled_t[s.name] + sweep_t[s.name] + proceeds_t[s.name]
                                  for s in debt_states},
            interest_by_tranche=dict(interest_t),
            reserve_balances={r.reserve_type: r.balance for r in reserve_states},
            reserve_draws=sum(r_draw.values()), reserve_releases=sum(r_release.values()),
            proceeds_applied=proceeds_to_debt, sweep_amount=swept_applied,
            junior_uses=junior, equity_distribution=equity_distribution,
            covenant_status=cov_status, dscr=dscr_value,
        ))
        ledgers.append(ledger)

    # --- Close source/use tie-out ------------------------------------------
    source_use = _close_source_use(deal)
    asrt.assert_source_use_close(source_use["sources"], source_use["uses"])

    return DealResult(
        deal_name=deal.name or "waterfall deal",
        periods=periods, ledgers=ledgers, audit_log=audit.records,
        tranche_summary=_tranche_summary(debt_states, equity_principal),
        covenant_status=[{"period": p.period_index, **p.covenant_status} for p in periods],
        source_use=source_use,
    )


# ==========================================================================
# Helpers
# ==========================================================================
def _fees_for_period(deal, t):
    total = 0.0
    for f in deal.fees:
        if f.period is None or f.period == t:
            total += f.amount
    return total


def _drawn_so_far(r_draw, reserve):
    return r_draw.get(reserve.reserve_type, 0.0)


def _pay_pro_rata(due_map, cash):
    """Pay each item pro-rata by amount due when cash is short; else pay in full."""
    total = sum(due_map.values())
    if total <= 0:
        return {k: 0.0 for k in due_map}
    if cash >= total:
        return dict(due_map)
    ratio = max(cash, 0.0) / total
    return {k: v * ratio for k, v in due_map.items()}


def _apply_prepayment(groups, amount, category, sweep_t, proceeds_t, period_index):
    """Apply ``amount`` to debt prepayment in strict priority order.

    ``groups`` is an ordered list of tranche-state groups (senior group, then
    mezzanine group). A junior group is only reached once every senior group is
    fully retired — never pari-passu across seniority (methodology step 5 / the
    separate proceeds path). Within a group, allocation is pro-rata by current
    balance (pari-passu). Returns the total applied.
    """
    remaining = max(amount, 0.0)
    applied_total = 0.0
    for group in groups:
        if remaining <= 1e-12:
            break
        applied = _apply_within_group(group, remaining, category, sweep_t,
                                      proceeds_t, period_index)
        applied_total += applied
        remaining -= applied
    return applied_total


def _apply_within_group(states, amount, category, sweep_t, proceeds_t, period_index):
    """Apply ``amount`` pro-rata by balance across one pari-passu group."""
    amount = max(amount, 0.0)
    total_bal = sum(s.balance for s in states)
    if amount <= 0 or total_bal <= 0:
        return 0.0
    applied_total = 0.0
    remaining = amount
    for s in states:
        if remaining <= 0 or s.balance <= 0:
            continue
        share = min(remaining, amount * (s.balance / total_bal), s.balance) \
            if amount < total_bal else min(remaining, s.balance)
        applied = s.apply_prepayment(share, category, period_index)
        applied_total += applied
        remaining -= applied
        if category == "sweep":
            sweep_t[s.name] += applied
        else:
            proceeds_t[s.name] += applied
    # Second pass for any rounding remainder (when amount < total_bal but not fully placed).
    if remaining > 1e-9:
        for s in states:
            if remaining <= 0:
                break
            applied = s.apply_prepayment(remaining, category, period_index)
            applied_total += applied
            remaining -= applied
            if category == "sweep":
                sweep_t[s.name] += applied
            else:
                proceeds_t[s.name] += applied
    return applied_total


def _mezz_ds_due(mezz_states, interest_t, t):
    total = 0.0
    for s in mezz_states:
        total += interest_t.get(s.name, 0.0)
        total += s.schedule[t] if t < len(s.schedule) else 0.0
    return total


def _evaluate_covenants(deal, t, cfads, senior_interest_due, senior_sched_due,
                        interest_t, mezz_states, senior_balance, total_debt,
                        periods_per_year, audit):
    senior_ds = sum(senior_interest_due.values()) + sum(senior_sched_due.values())
    mezz_ds = sum(interest_t.get(s.name, 0.0) + (s.schedule[t] if t < len(s.schedule) else 0.0)
                  for s in mezz_states)
    dscr_senior = cov.dscr(cfads, senior_ds, mezz_ds, "senior")
    # LLCR and PLCR use DISTINCT horizons (methodology Covenant Pack):
    #   LLCR = PV(CFADS to *loan maturity*) / senior balance
    #   PLCR = PV(CFADS to *end of project life*) / senior balance  (PF-only)
    # The senior loan matures at the latest senior term; project life extends
    # beyond it via project_life_periods.
    n = deal.num_periods
    llcr_end = max(min(tr.term_periods or n, n) for tr in deal.senior_tranches)
    llcr_future = [float(x) for x in deal.cfads_stream[t + 1: llcr_end]]
    plcr_end = min(deal.project_life_periods, n) if deal.project_life_periods else n
    plcr_future = [float(x) for x in deal.cfads_stream[t + 1: plcr_end]]
    senior_cost = _weighted_senior_cost(deal) / periods_per_year
    if any(c.metric in ("LLCR", "PLCR") for c in deal.covenants):
        audit.record(t, "discount_rate",
                     f"LLCR/PLCR present-valued at the weighted senior debt cost "
                     f"{senior_cost:.6f} per period")

    status = {}
    for c in deal.covenants:
        if c.metric == "DSCR":
            value = cov.dscr(cfads, senior_ds, mezz_ds, c.denominator)
        elif c.metric == "LLCR":
            value = cov.llcr(llcr_future, senior_balance, senior_cost)
        elif c.metric == "PLCR":
            value = cov.plcr(plcr_future, senior_balance, senior_cost, deal.deal_type)
        elif c.metric == "LTV":
            value = cov.ltv(total_debt, deal.asset_value or 0.0)
        elif c.metric == "debt_yield":
            value = cov.debt_yield(cfads * periods_per_year, total_debt)
        elif c.metric == "interest_coverage":
            value = cov.interest_coverage(cfads, sum(senior_interest_due.values()))
        else:
            value = float("nan")
        tier = cov.evaluate(c, value)
        status[c.metric] = tier
        if tier in ("trap", "default"):
            audit.record(t, f"covenant_{c.metric}",
                         f"{c.metric} test result {value:.4f} -> {tier} tier — {MECHANICAL_TEST_LABEL}",
                         mechanical_test_result=True)
    return status, dscr_senior


def _weighted_senior_cost(deal):
    tot = sum(t.principal for t in deal.senior_tranches)
    if tot <= 0:
        return 0.0
    return sum(t.principal * t.coupon for t in deal.senior_tranches) / tot


def _tranche_summary(debt_states, equity_principal):
    rows = [{"tranche": s.name, "type": s.tranche.tranche_type,
             "original_principal": s.tranche.principal, "ending_balance": s.balance}
            for s in debt_states]
    rows.append({"tranche": "equity", "type": "equity",
                 "original_principal": equity_principal, "ending_balance": None})
    return rows


def _close_source_use(deal):
    sources = sum(t.principal for t in deal.tranches)          # debt + equity
    reserve_open = sum(r.opening_balance for r in deal.reserves)
    if deal.project_cost is not None:
        uses = deal.project_cost + reserve_open
    else:
        uses = sources   # ties out trivially when no uses-of-funds supplied
    return {"sources": sources, "uses": uses,
            "debt": sum(t.principal for t in deal.tranches if t.is_debt),
            "equity": sum(t.principal for t in deal.equity_tranches),
            "funded_reserves": reserve_open}
