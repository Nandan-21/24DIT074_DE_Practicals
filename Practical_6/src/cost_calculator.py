from typing import Dict, List

class StorageCostCalculator:
    """Calculates illustrative storage costs and tiering savings."""

    def __init__(self, hot_rate: float = 0.023, warm_rate: float = 0.0125, cold_rate: float = 0.004):
        self.hot_rate = hot_rate
        self.warm_rate = warm_rate
        self.cold_rate = cold_rate

    def calculate_savings(self, evaluated_objects: List[Dict]) -> Dict:
        """
        Calculates monthly storage costs comparing all-hot baseline vs tiered policy.
        """
        hot_bytes = 0
        warm_bytes = 0
        cold_bytes = 0
        total_bytes = 0

        for obj in evaluated_objects:
            size = obj.get("size_bytes", 0)
            tier = obj.get("target_tier", "HOT")
            total_bytes += size

            if tier == "HOT":
                hot_bytes += size
            elif tier == "WARM":
                warm_bytes += size
            elif tier in ["COLD", "EXPIRED"]:
                # Cold objects are compressed ~50%
                compressed_size = obj.get("transition_details", {}).get("dest_size", int(size * 0.45))
                cold_bytes += compressed_size

        total_gb = total_bytes / (1024 ** 3)
        hot_gb = hot_bytes / (1024 ** 3)
        warm_gb = warm_bytes / (1024 ** 3)
        cold_gb = cold_bytes / (1024 ** 3)

        # Baseline: everything kept in HOT tier without compression
        baseline_cost = total_gb * self.hot_rate

        # Tiered cost
        tiered_hot_cost = hot_gb * self.hot_rate
        tiered_warm_cost = warm_gb * self.warm_rate
        tiered_cold_cost = cold_gb * self.cold_rate
        total_tiered_cost = tiered_hot_cost + tiered_warm_cost + tiered_cold_cost

        savings_usd = baseline_cost - total_tiered_cost
        savings_pct = (savings_usd / baseline_cost * 100) if baseline_cost > 0 else 0.0

        return {
            "total_objects": len(evaluated_objects),
            "total_size_bytes": total_bytes,
            "total_size_gb": round(total_gb, 6),
            "tier_breakdown": {
                "HOT": {"bytes": hot_bytes, "gb": round(hot_gb, 6), "monthly_cost_usd": round(tiered_hot_cost, 6)},
                "WARM": {"bytes": warm_bytes, "gb": round(warm_gb, 6), "monthly_cost_usd": round(tiered_warm_cost, 6)},
                "COLD": {"bytes": cold_bytes, "gb": round(cold_gb, 6), "monthly_cost_usd": round(tiered_cold_cost, 6)}
            },
            "baseline_all_hot_cost_usd": round(baseline_cost, 6),
            "optimized_tiered_cost_usd": round(total_tiered_cost, 6),
            "monthly_savings_usd": round(savings_usd, 6),
            "savings_percentage": round(savings_pct, 2),
            "rates_used_per_gb_month": {
                "HOT": self.hot_rate,
                "WARM": self.warm_rate,
                "COLD": self.cold_rate
            }
        }
