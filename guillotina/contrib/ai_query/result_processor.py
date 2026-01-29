from typing import Dict
from typing import List
from typing import Optional

import logging


logger = logging.getLogger("guillotina")


class ResultProcessor:
    """
    Process and aggregate search results generically.
    """

    @staticmethod
    def process_results(
        results: Dict,
        aggregation_config: Optional[Dict] = None,
    ) -> Dict:
        """
        Process search results and apply aggregations if needed.
        """
        if not aggregation_config:
            return results

        items = results.get("items", [])
        items_total = results.get("items_total")
        operation = aggregation_config.get("operation")
        field = aggregation_config.get("field")
        group_by = aggregation_config.get("group_by")

        if operation == "count" and not group_by:
            total = items_total if items_total is not None else len(items)
            return {"count": total}
        if not items:
            return results

        if operation == "sum":
            return ResultProcessor._sum_aggregation(items, field, group_by)
        elif operation == "count":
            return ResultProcessor._count_aggregation(items, field, group_by)
        elif operation == "average":
            return ResultProcessor._average_aggregation(items, field, group_by)
        else:
            logger.warning(f"Unknown aggregation operation: {operation}")
            return results

    @staticmethod
    def _sum_aggregation(
        items: List[Dict], field: str, group_by: Optional[str] = None
    ) -> Dict:
        """Sum numeric field values, optionally grouped by another field."""
        if group_by:
            grouped = {}
            for item in items:
                group_key = item.get(group_by, "unknown")
                value = ResultProcessor._get_numeric_value(item, field)
                grouped[group_key] = grouped.get(group_key, 0) + value
            return {"by_" + group_by: grouped, "total": sum(grouped.values())}
        else:
            total = sum(ResultProcessor._get_numeric_value(item, field) for item in items)
            return {"total": total, "items_count": len(items)}

    @staticmethod
    def _count_aggregation(
        items: List[Dict], field: Optional[str] = None, group_by: Optional[str] = None
    ) -> Dict:
        """Count items, optionally grouped by field."""
        if group_by:
            grouped = {}
            for item in items:
                group_key = item.get(group_by, "unknown")
                grouped[group_key] = grouped.get(group_key, 0) + 1
            return {"by_" + group_by: grouped, "total": len(items)}
        else:
            return {"count": len(items)}

    @staticmethod
    def _average_aggregation(
        items: List[Dict], field: str, group_by: Optional[str] = None
    ) -> Dict:
        """Calculate average of numeric field, optionally grouped."""
        if group_by:
            grouped = {}
            counts = {}
            for item in items:
                group_key = item.get(group_by, "unknown")
                value = ResultProcessor._get_numeric_value(item, field)
                grouped[group_key] = grouped.get(group_key, 0) + value
                counts[group_key] = counts.get(group_key, 0) + 1

            averages = {
                k: v / counts[k] if counts[k] > 0 else 0
                for k, v in grouped.items()
            }
            return {"by_" + group_by: averages, "overall_average": sum(grouped.values()) / len(items) if items else 0}
        else:
            total = sum(ResultProcessor._get_numeric_value(item, field) for item in items)
            return {"average": total / len(items) if items else 0, "items_count": len(items)}

    @staticmethod
    def _get_numeric_value(item: Dict, field: str) -> float:
        """Extract numeric value from item, handling nested fields."""
        value = item.get(field, 0)
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {field} to numeric: {value}")
            return 0.0
