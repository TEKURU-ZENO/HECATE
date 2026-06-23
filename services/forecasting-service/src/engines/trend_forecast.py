import numpy as np
from scipy import stats


def fit_and_predict(values: list[float], next_steps: int = 15, threshold: float = 85.0) -> dict:
    n = len(values)
    if n < 5:
        # Not enough points for a reliable linear fit
        return {
            "predicted_value": float(values[-1]) if n > 0 else 0.0,
            "lower_bound": float(values[-1]) if n > 0 else 0.0,
            "upper_bound": float(values[-1]) if n > 0 else 0.0,
            "confidence": 0.1,
            "lead_time_seconds": 0,
        }

    x = np.arange(1, n + 1)
    y = np.array(values)

    # Fit linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    # Predict next steps
    x_future = np.arange(n + 1, n + 1 + next_steps)
    y_pred = slope * x_future + intercept

    # Calculate confidence interval bands
    residuals = y - (slope * x + intercept)
    dof = n - 2
    if dof > 0:
        s_err_est = np.sqrt(np.sum(residuals**2) / dof)
    else:
        s_err_est = 0.0

    x_mean = np.mean(x)
    x_ss = np.sum((x - x_mean) ** 2)

    if dof > 0:
        t_val = stats.t.ppf(0.975, dof)
    else:
        t_val = 1.96

    y_err = []
    for x_f in x_future:
        if x_ss > 0:
            se = s_err_est * np.sqrt(1.0 + 1.0 / n + ((x_f - x_mean) ** 2) / x_ss)
        else:
            se = s_err_est * np.sqrt(1.0 + 1.0 / n)
        y_err.append(t_val * se)

    y_err = np.array(y_err)
    y_lower = y_pred - y_err
    y_upper = y_pred + y_err

    # Compute prediction confidence
    r_squared = r_value**2 if not np.isnan(r_value) else 0.0
    confidence = float(r_squared)

    # Adjust confidence if trend is flat or downward (stable)
    if slope <= 0:
        confidence = max(0.1, confidence * 0.5)

    if np.isnan(confidence) or confidence < 0.1:
        confidence = 0.1
    elif confidence > 0.99:
        confidence = 0.99

    # Find lead time
    lead_time_steps = -1
    for idx, val in enumerate(y_pred):
        if slope > 0 and val >= threshold:
            lead_time_steps = idx + 1
            break

    if lead_time_steps != -1:
        # Assuming scrape interval is 5 seconds
        lead_time_seconds = lead_time_steps * 5
    else:
        lead_time_seconds = 0

    return {
        "predicted_value": round(float(y_pred[-1]), 2),
        "lower_bound": round(float(y_lower[-1]), 2),
        "upper_bound": round(float(y_upper[-1]), 2),
        "confidence": round(confidence, 2),
        "lead_time_seconds": lead_time_seconds,
    }
