import math
from typing import List, Dict, Any, Tuple
import numpy as np

class StatisticalAnalyzer:
    @staticmethod
    def welch_t_test(group1: List[float], group2: List[float]) -> Tuple[float, float]:
        """Performs Welch's t-test and returns t-statistic and approximate p-value."""
        n1 = len(group1)
        n2 = len(group2)
        if n1 < 2 or n2 < 2:
            return 0.0, 1.0

        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        # Welch's t-statistic
        se = math.sqrt(var1/n1 + var2/n2)
        if se == 0.0:
            return 0.0, 1.0
            
        t_stat = (mean1 - mean2) / se

        # Degrees of freedom (Welch-Satterthwaite equation)
        df_num = (var1/n1 + var2/n2)**2
        df_den = (var1/n1)**2 / (n1 - 1) + (var2/n2)**2 / (n2 - 1)
        df = df_num / df_den if df_den != 0 else 1.0

        # Normal approximation of p-value (two-tailed)
        p_val = 2.0 * (1.0 - StatisticalAnalyzer._std_normal_cdf(abs(t_stat)))
        return t_stat, p_val

    @staticmethod
    def cohens_d(group1: List[float], group2: List[float]) -> float:
        """Calculates Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        if n1 < 2 or n2 < 2:
            return 0.0
            
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        if pooled_std == 0.0:
            return 0.0
        return (mean1 - mean2) / pooled_std

    @staticmethod
    def bootstrap_ci(data: List[float], repetitions: int = 1000, conf_level: float = 0.95) -> Tuple[float, float]:
        """Estimates confidence interval using bootstrapping."""
        n = len(data)
        if n == 0:
            return 0.0, 0.0
            
        arr = np.array(data)
        means = []
        # Seeded rng for bootstrap
        rng = np.random.default_rng(1002)
        for _ in range(repetitions):
            sample = rng.choice(arr, size=n, replace=True)
            means.append(np.mean(sample))

        alpha = 1.0 - conf_level
        lower = float(np.percentile(means, alpha / 2.0 * 100))
        upper = float(np.percentile(means, (1.0 - alpha / 2.0) * 100))
        return lower, upper

    @staticmethod
    def _std_normal_cdf(x: float) -> float:
        """Standard Normal Cumulative Distribution Function approximation."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @staticmethod
    def mann_whitney_u(group1: List[float], group2: List[float]) -> Tuple[float, float]:
        """Calculates Mann-Whitney U test statistic."""
        n1, n2 = len(group1), len(group2)
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0
            
        # Combine and rank
        combined = [(val, 1) for val in group1] + [(val, 2) for val in group2]
        combined.sort(key=lambda x: x[0])
        
        ranks = {}
        for rank, (val, group) in enumerate(combined, 1):
            ranks.setdefault(val, []).append(rank)
            
        # Mean rank for ties
        mean_ranks = {val: sum(r_list)/len(r_list) for val, r_list in ranks.items()}
        
        rank_sum_1 = sum(mean_ranks[val] for val, group in combined if group == 1)
        
        u1 = rank_sum_1 - (n1 * (n1 + 1)) / 2.0
        u2 = n1 * n2 - u1
        u_stat = min(u1, u2)
        
        # Large sample approximation p-value
        mean_u = (n1 * n2) / 2.0
        var_u = (n1 * n2 * (n1 + n2 + 1)) / 12.0
        if var_u == 0.0:
            return u_stat, 1.0
            
        z_stat = (u_stat - mean_u) / math.sqrt(var_u)
        p_val = 2.0 * StatisticalAnalyzer._std_normal_cdf(z_stat)
        return u_stat, p_val
