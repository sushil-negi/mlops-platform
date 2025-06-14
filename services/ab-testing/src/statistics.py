"""
Statistical analysis for A/B test results
Determines if differences are statistically significant
"""

from typing import Dict, List

import numpy as np
import scipy.stats as stats
import structlog

logger = structlog.get_logger()


class ABTestAnalyzer:
    """Statistical analysis for A/B testing results"""

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.alpha = 1 - confidence_level

    def analyze_experiment(self, experiment_data: Dict) -> Dict:
        """
        Perform comprehensive statistical analysis of A/B test

        Args:
            experiment_data: Dictionary containing metrics for model_a and model_b

        Returns:
            Dictionary with analysis results and recommendations
        """
        try:
            model_a_data = experiment_data.get("model_a", {})
            model_b_data = experiment_data.get("model_b", {})

            if not model_a_data or not model_b_data:
                return {
                    "status": "insufficient_data",
                    "message": "No data available for one or both models",
                }

            results = {
                "confidence_level": self.confidence_level,
                "analysis_timestamp": str(np.datetime64("now")),
                "metrics": {},
                "overall_recommendation": {},
                "statistical_power": {},
                "effect_sizes": {},
            }

            # Analyze each metric
            metrics_to_analyze = [
                "accuracy",
                "empathy_score",
                "response_time",
                "crisis_detection_rate",
            ]

            for metric in metrics_to_analyze:
                if metric in model_a_data and metric in model_b_data:
                    metric_analysis = self._analyze_metric(
                        metric, model_a_data[metric], model_b_data[metric]
                    )
                    results["metrics"][metric] = metric_analysis

            # Generate overall recommendation
            results["overall_recommendation"] = self._generate_recommendation(
                results["metrics"]
            )

            # Calculate statistical power
            results["statistical_power"] = self._calculate_statistical_power(
                results["metrics"]
            )

            return results

        except Exception as e:
            logger.error("Error in statistical analysis", error=str(e))
            return {"status": "error", "message": str(e)}

    def _analyze_metric(
        self, metric_name: str, values_a: List[float], values_b: List[float]
    ) -> Dict:
        """Analyze a specific metric between two groups"""

        if not values_a or not values_b:
            return {
                "status": "no_data",
                "message": f"No data available for {metric_name}",
            }

        # Convert to numpy arrays
        a = np.array(values_a)
        b = np.array(values_b)

        # Basic statistics
        mean_a = np.mean(a)
        mean_b = np.mean(b)
        std_a = np.std(a, ddof=1) if len(a) > 1 else 0
        std_b = np.std(b, ddof=1) if len(b) > 1 else 0

        # Sample sizes
        n_a = len(a)
        n_b = len(b)

        # Check minimum sample size
        min_sample_size = 30
        if n_a < min_sample_size or n_b < min_sample_size:
            return {
                "status": "insufficient_samples",
                "message": f"Need at least {min_sample_size} samples per group",
                "sample_size_a": n_a,
                "sample_size_b": n_b,
                "mean_a": mean_a,
                "mean_b": mean_b,
            }

        # Perform t-test
        try:
            # Check if variances are equal (Levene's test)
            levene_stat, levene_p = stats.levene(a, b)
            equal_var = levene_p > 0.05

            # Two-sample t-test
            t_stat, p_value = stats.ttest_ind(a, b, equal_var=equal_var)

            # Effect size (Cohen's d)
            pooled_std = np.sqrt(
                ((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2)
            )
            cohens_d = (mean_b - mean_a) / pooled_std if pooled_std > 0 else 0

            # Confidence interval for difference in means
            se_diff = pooled_std * np.sqrt(1 / n_a + 1 / n_b)
            degrees_freedom = n_a + n_b - 2
            t_critical = stats.t.ppf(1 - self.alpha / 2, degrees_freedom)

            diff_mean = mean_b - mean_a
            ci_lower = diff_mean - t_critical * se_diff
            ci_upper = diff_mean + t_critical * se_diff

            # Practical significance thresholds
            practical_thresholds = {
                "accuracy": 0.02,  # 2% improvement
                "empathy_score": 0.05,  # 5% improvement
                "response_time": 0.1,  # 100ms improvement
                "crisis_detection_rate": 0.005,  # 0.5% improvement
            }

            practical_threshold = practical_thresholds.get(metric_name, 0.01)

            # Determine significance
            is_statistically_significant = p_value < self.alpha
            is_practically_significant = abs(diff_mean) >= practical_threshold

            # Direction of effect
            if diff_mean > 0:
                direction = "Model B is better"
                improvement_pct = (
                    ((mean_b - mean_a) / mean_a) * 100 if mean_a != 0 else 0
                )
            elif diff_mean < 0:
                direction = "Model A is better"
                improvement_pct = (
                    ((mean_a - mean_b) / mean_b) * 100 if mean_b != 0 else 0
                )
            else:
                direction = "No difference"
                improvement_pct = 0

            # Interpretation of effect size
            if abs(cohens_d) < 0.2:
                effect_interpretation = "negligible"
            elif abs(cohens_d) < 0.5:
                effect_interpretation = "small"
            elif abs(cohens_d) < 0.8:
                effect_interpretation = "medium"
            else:
                effect_interpretation = "large"

            return {
                "status": "analyzed",
                "sample_size_a": n_a,
                "sample_size_b": n_b,
                "mean_a": float(mean_a),
                "mean_b": float(mean_b),
                "std_a": float(std_a),
                "std_b": float(std_b),
                "difference": float(diff_mean),
                "improvement_percentage": float(improvement_pct),
                "p_value": float(p_value),
                "t_statistic": float(t_stat),
                "cohens_d": float(cohens_d),
                "effect_interpretation": effect_interpretation,
                "confidence_interval": {
                    "lower": float(ci_lower),
                    "upper": float(ci_upper),
                    "level": self.confidence_level,
                },
                "statistically_significant": is_statistically_significant,
                "practically_significant": is_practically_significant,
                "direction": direction,
                "equal_variances": equal_var,
                "recommendation": self._get_metric_recommendation(
                    metric_name,
                    is_statistically_significant,
                    is_practically_significant,
                    diff_mean,
                    cohens_d,
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing {metric_name}", error=str(e))
            return {
                "status": "error",
                "message": str(e),
                "mean_a": float(mean_a),
                "mean_b": float(mean_b),
            }

    def _get_metric_recommendation(
        self,
        metric_name: str,
        stat_sig: bool,
        pract_sig: bool,
        diff: float,
        effect_size: float,
    ) -> str:
        """Generate recommendation for a specific metric"""

        if not stat_sig:
            return (
                "No statistically significant difference detected. Continue monitoring."
            )

        if not pract_sig:
            return (
                "Statistically significant but not practically meaningful difference."
            )

        # Healthcare-specific recommendations
        if metric_name == "crisis_detection_rate":
            if diff > 0:
                return "Model B shows improved crisis detection. Recommend gradual rollout with monitoring."
            else:
                return "Model B shows decreased crisis detection. DO NOT DEPLOY - safety risk."

        elif metric_name == "accuracy":
            if diff > 0:
                return f"Model B shows {abs(diff)*100:.1f}% accuracy improvement. Recommend deployment."
            else:
                return f"Model B shows {abs(diff)*100:.1f}% accuracy decrease. Consider further training."

        elif metric_name == "empathy_score":
            if diff > 0:
                return f"Model B shows improved empathy. Recommend deployment for better user experience."
            else:
                return f"Model B shows decreased empathy. Consider empathy-focused training."

        elif metric_name == "response_time":
            if diff < 0:  # Lower is better for response time
                return (
                    f"Model B is {abs(diff)*1000:.0f}ms faster. Recommend deployment."
                )
            else:
                return f"Model B is {diff*1000:.0f}ms slower. Consider optimization."

        return "Significant difference detected. Review impact carefully."

    def _generate_recommendation(self, metrics_analysis: Dict) -> Dict:
        """Generate overall experiment recommendation"""

        if not metrics_analysis:
            return {
                "decision": "insufficient_data",
                "reason": "No metrics available for analysis",
            }

        # Count significant improvements/regressions
        improvements = 0
        regressions = 0
        safety_issues = 0

        critical_metrics = ["crisis_detection_rate"]
        important_metrics = ["accuracy", "empathy_score"]

        for metric, analysis in metrics_analysis.items():
            if analysis.get("status") != "analyzed":
                continue

            is_sig = analysis.get("statistically_significant", False)
            is_pract = analysis.get("practically_significant", False)
            diff = analysis.get("difference", 0)

            if is_sig and is_pract:
                if metric in critical_metrics:
                    if diff < 0:  # Regression in critical metric
                        safety_issues += 1
                    else:
                        improvements += 1
                elif metric in important_metrics:
                    if diff > 0:
                        improvements += 1
                    else:
                        regressions += 1
                elif metric == "response_time":
                    if diff < 0:  # Lower response time is better
                        improvements += 1
                    else:
                        regressions += 1

        # Decision logic
        if safety_issues > 0:
            return {
                "decision": "reject",
                "reason": "Safety regressions detected in critical metrics",
                "confidence": "high",
                "action": "Do not deploy Model B. Address safety issues.",
            }

        if improvements > regressions:
            confidence = "high" if improvements >= 2 else "medium"
            return {
                "decision": "accept",
                "reason": f"Model B shows {improvements} significant improvements vs {regressions} regressions",
                "confidence": confidence,
                "action": "Deploy Model B with gradual rollout and monitoring.",
            }

        elif regressions > improvements:
            return {
                "decision": "reject",
                "reason": f"Model B shows {regressions} significant regressions vs {improvements} improvements",
                "confidence": "medium",
                "action": "Continue with Model A. Consider additional training for Model B.",
            }

        else:
            return {
                "decision": "inconclusive",
                "reason": "No clear winner. Results are mixed or inconclusive.",
                "confidence": "low",
                "action": "Extend experiment duration or collect more data.",
            }

    def _calculate_statistical_power(self, metrics_analysis: Dict) -> Dict:
        """Calculate statistical power for the experiment"""

        power_results = {}

        for metric, analysis in metrics_analysis.items():
            if analysis.get("status") != "analyzed":
                continue

            try:
                n_a = analysis.get("sample_size_a", 0)
                n_b = analysis.get("sample_size_b", 0)
                effect_size = abs(analysis.get("cohens_d", 0))

                if n_a > 0 and n_b > 0:
                    # Calculate power using effect size
                    power = self._calculate_power_for_effect_size(n_a, n_b, effect_size)

                    # Calculate required sample size for 80% power
                    required_n = self._calculate_required_sample_size(effect_size, 0.8)

                    power_results[metric] = {
                        "current_power": float(power),
                        "effect_size": float(effect_size),
                        "sample_size_a": n_a,
                        "sample_size_b": n_b,
                        "required_sample_size_for_80_power": required_n,
                        "adequate_power": power >= 0.8,
                    }

            except Exception as e:
                logger.error(f"Error calculating power for {metric}", error=str(e))

        return power_results

    def _calculate_power_for_effect_size(
        self, n1: int, n2: int, effect_size: float
    ) -> float:
        """Calculate statistical power given sample sizes and effect size"""
        try:
            # Simplified power calculation for two-sample t-test
            # This is an approximation
            n_harmonic = 2 * n1 * n2 / (n1 + n2)  # Harmonic mean of sample sizes
            delta = effect_size * np.sqrt(n_harmonic / 2)

            # Power = P(reject H0 | H1 is true)
            critical_value = stats.norm.ppf(1 - self.alpha / 2)
            power = (
                1
                - stats.norm.cdf(critical_value - delta)
                + stats.norm.cdf(-critical_value - delta)
            )

            return min(max(power, 0), 1)  # Constrain to [0, 1]

        except:
            return 0.5  # Default if calculation fails

    def _calculate_required_sample_size(
        self, effect_size: float, desired_power: float = 0.8
    ) -> int:
        """Calculate required sample size for desired power"""
        try:
            if effect_size <= 0:
                return 10000  # Very large number if no effect

            # Simplified calculation
            z_alpha = stats.norm.ppf(1 - self.alpha / 2)
            z_beta = stats.norm.ppf(desired_power)

            n = 2 * ((z_alpha + z_beta) / effect_size) ** 2

            return max(int(np.ceil(n)), 30)  # Minimum 30 samples

        except:
            return 1000  # Default if calculation fails
