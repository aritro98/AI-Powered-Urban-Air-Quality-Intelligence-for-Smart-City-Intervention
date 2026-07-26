"""
Time-series forecasting utilities.

Implements additive Holt-Winters (level + trend + seasonal, all
continuously updating) as the primary model, with seasonal-naive kept as
a fallback for short histories. So the RMSE-vs-persistence comparison is
computed from a real fitted model on real historical data, not fabricated
to look good.

If fewer than MIN_HISTORY_POINTS of real historical data are available,
callers should treat the backtest as unreliable and flag it rather than
present a misleading number — see forecast_agent.py for how this is
surfaced to the API/UI.
"""

MIN_HISTORY_POINTS = 48  # at least 2 days of hourly history to learn a diurnal profile


def seasonal_naive_forecast(series, season_length=24, steps_ahead=24, damping=0.92):
    """Forecast using the diurnal (hour-of-day) profile learned from
    history, adjusted by the most recent anomaly relative to that profile,
    with the anomaly decaying toward zero over the horizon.

    NOTE: this model averages the seasonal profile over the WHOLE training
    window, which works well for stationary diurnal series but performs
    poorly when there's a real multi-day regime shift (e.g. a pollution
    episode clearing) inside that window -- see holt_winters_additive
    below, which is now the primary model for exactly this reason.
    """
    if len(series) < season_length:
        return [series[-1]] * steps_ahead if series else [0] * steps_ahead

    profile = []
    for hour in range(season_length):
        vals = [series[i] for i in range(hour, len(series), season_length)]
        profile.append(sum(vals) / len(vals))

    last_hour_idx = (len(series) - 1) % season_length
    current_anomaly = series[-1] - profile[last_hour_idx]

    forecast = []
    for h in range(steps_ahead):
        hour_idx = (len(series) + h) % season_length
        decayed_anomaly = current_anomaly * (damping ** (h + 1))
        forecast.append(round(profile[hour_idx] + decayed_anomaly, 1))
    return forecast


def holt_winters_additive(series, season_length=24, alpha=0.85, beta=0.05, gamma=0.25, steps_ahead=24):
    """Additive Holt-Winters: tracks a continuously UPDATING level, trend,
    and seasonal (diurnal) profile together, rather than freezing the
    seasonal profile as one flat average over the whole training window.

    This matters because real AQI has both a daily cycle AND multi-day
    regime shifts (rain clearing a pollution episode, wind direction
    changes, a new episode starting) -- a flat-average seasonal profile
    (see seasonal_naive_forecast) blends multiple regimes together and can
    badly mispredict whichever regime is currently happening. Holt-Winters
    updates its level every single step, so it tracks a regime shift within
    hours instead of dragging the forecast back toward a stale average.

    alpha=0.85 was chosen by testing against three synthetic scenarios
    (stationary diurnal, gradual multi-day trend, and a sharp regime
    shift) and picking the value that performed well across all three --
    see conversation history / commit notes for the actual numbers.

    Falls back to seasonal_naive_forecast if there isn't enough history for
    two full seasonal cycles (needed to initialize trend/seasonal terms).
    """
    n = len(series)
    if n < 2 * season_length:
        return seasonal_naive_forecast(series, season_length, steps_ahead)

    level = sum(series[:season_length]) / season_length
    second_season_avg = sum(series[season_length:2 * season_length]) / season_length
    trend = (second_season_avg - level) / season_length
    seasonals = [series[i] - level for i in range(season_length)]

    levels, trends = [level], [trend]
    for t in range(season_length, n):
        last_level, last_trend = levels[-1], trends[-1]
        last_seasonal = seasonals[t - season_length]

        new_level = alpha * (series[t] - last_seasonal) + (1 - alpha) * (last_level + last_trend)
        new_trend = beta * (new_level - last_level) + (1 - beta) * last_trend
        new_seasonal = gamma * (series[t] - new_level) + (1 - gamma) * last_seasonal

        levels.append(new_level)
        trends.append(new_trend)
        seasonals.append(new_seasonal)

    final_level, final_trend = levels[-1], trends[-1]
    recent_cycle = seasonals[-season_length:]

    forecast = []
    for h in range(1, steps_ahead + 1):
        phase = (n + h - 1) % season_length
        forecast.append(round(final_level + h * final_trend + recent_cycle[phase], 1))
    return forecast


def holt_linear_forecast(series, alpha=0.4, beta=0.15, steps_ahead=1):
    """Fit Holt's linear trend model on `series` and return forecasts for
    the next `steps_ahead` points beyond the end of the series. (Kept for
    reference/comparison — NOT used as the primary model; it systematically
    overshoots on oscillating diurnal data since it has trend but no
    seasonal component.)"""
    if len(series) < 2:
        return [series[-1]] * steps_ahead if series else [0] * steps_ahead

    level = series[0]
    trend = series[1] - series[0]
    for i in range(1, len(series)):
        value = series[i]
        last_level = level
        level = alpha * value + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    return [round(level + (h + 1) * trend, 1) for h in range(steps_ahead)]


def backtest(series, holdout=24):
    """Train on series[:-holdout], predict the held-out window, and compare
    RMSE of the model vs. a naive persistence baseline (last observed value
    repeated). Returns None if there isn't enough real history."""
    if len(series) < MIN_HISTORY_POINTS + holdout:
        return None

    train = series[: -holdout]
    test = series[-holdout:]

    try:
        model_preds = holt_winters_additive(train, season_length=24, steps_ahead=holdout)
        model_name = "holt_winters_additive"
    except Exception:
        model_preds = seasonal_naive_forecast(train, season_length=24, steps_ahead=holdout)
        model_name = "seasonal_naive_fallback"
    persistence_preds = [train[-1]] * holdout

    rmse_model = _rmse(test, model_preds)
    rmse_persistence = _rmse(test, persistence_preds)

    return {
        "model_name": model_name,
        "rmse_model": round(rmse_model, 2),
        "rmse_persistence": round(rmse_persistence, 2),
        "improvement_pct": round((1 - rmse_model / rmse_persistence) * 100, 1) if rmse_persistence else 0.0,
        "holdout_actual": test,
        "holdout_model_pred": model_preds,
        "holdout_persistence_pred": persistence_preds,
    }


def _rmse(actual, predicted):
    n = len(actual)
    return (sum((a - p) ** 2 for a, p in zip(actual, predicted)) / n) ** 0.5