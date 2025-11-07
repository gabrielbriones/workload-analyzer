"""Custom analysis module for natural language queries."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ..config import Settings
from ..exceptions import AnalysisError
from ..services.iss_client import ISSClient

logger = logging.getLogger(__name__)


class CustomAnalyzer:
    """Analyzer for custom natural language queries."""

    def __init__(self, iss_client: ISSClient, settings: Settings):
        """Initialize the custom analyzer."""
        self.iss_client = iss_client
        self.settings = settings

    async def analyze_custom_query(
        self,
        query: str,
        scope: str = "all",
        entity_id: Optional[str] = None,
        time_range_days: int = 30,
        include_ai_analysis: bool = True,
    ) -> Dict[str, Any]:
        """Perform custom analysis based on natural language query.

        Args:
            query: Natural language analysis query
            scope: Analysis scope (job, platform, instance, all)
            entity_id: Specific entity ID to analyze
            time_range_days: Time range for analysis
            include_ai_analysis: Include AI interpretation

        Returns:
            Custom analysis results
        """
        try:
            logger.info(f"Processing custom query: '{query}' with scope: {scope}")

            # Parse the query to extract intent and parameters
            analysis_intent = await self._parse_query_intent(query)

            # Gather relevant data based on scope and intent
            data = await self._gather_analysis_data(
                scope, entity_id, time_range_days, analysis_intent
            )

            # Perform analysis based on intent
            analysis_results = await self._perform_custom_analysis(
                query, analysis_intent, data
            )

            # Generate summary and findings
            summary, key_findings = await self._generate_custom_summary(
                query, analysis_results
            )

            # Generate recommendations
            recommendations = await self._generate_custom_recommendations(
                analysis_intent, analysis_results
            )

            # Generate AI analysis
            ai_analysis = None
            confidence_score = None
            if include_ai_analysis:
                ai_analysis, confidence_score = await self._generate_ai_custom_analysis(
                    query, analysis_intent, analysis_results
                )

            return {
                "summary": summary,
                "key_findings": key_findings,
                "recommendations": recommendations,
                "ai_analysis": ai_analysis,
                "confidence_score": confidence_score,
                "analysis_intent": analysis_intent,
                "data_scope": scope,
                "entity_count": len(data.get("entities", [])),
            }

        except Exception as e:
            logger.error(f"Error in custom analysis: {e}")
            raise AnalysisError(f"Custom analysis failed: {e}")

    async def _parse_query_intent(self, query: str) -> Dict[str, Any]:
        """Parse natural language query to extract analysis intent.

        Args:
            query: Natural language query

        Returns:
            Analysis intent dictionary
        """
        try:
            query_lower = query.lower()
            intent = {
                "type": "general",
                "metrics": [],
                "filters": {},
                "comparisons": [],
                "time_focus": None,
                "aggregation": None,
            }

            # Identify analysis type
            if any(
                word in query_lower
                for word in ["performance", "speed", "runtime", "execution"]
            ):
                intent["type"] = "performance"
            elif any(
                word in query_lower
                for word in ["resource", "cpu", "memory", "utilization"]
            ):
                intent["type"] = "resource"
            elif any(
                word in query_lower
                for word in ["error", "fail", "success", "reliability"]
            ):
                intent["type"] = "reliability"
            elif any(
                word in query_lower for word in ["cost", "efficiency", "optimization"]
            ):
                intent["type"] = "optimization"
            elif any(
                word in query_lower
                for word in ["trend", "over time", "historical", "pattern"]
            ):
                intent["type"] = "trend"
            elif any(
                word in query_lower
                for word in ["compare", "comparison", "versus", "vs"]
            ):
                intent["type"] = "comparison"

            # Extract metrics
            metric_patterns = {
                "runtime": ["runtime", "execution time", "duration"],
                "cpu": ["cpu", "processor", "compute"],
                "memory": ["memory", "ram", "mem"],
                "success_rate": ["success", "completion", "reliability"],
                "error_rate": ["error", "failure", "fail"],
                "throughput": ["throughput", "jobs per hour", "rate"],
                "queue_time": ["queue", "wait", "delay"],
            }

            for metric, patterns in metric_patterns.items():
                if any(pattern in query_lower for pattern in patterns):
                    intent["metrics"].append(metric)

            # Extract time focus
            if any(word in query_lower for word in ["yesterday", "today", "recent"]):
                intent["time_focus"] = "recent"
            elif any(word in query_lower for word in ["week", "weekly"]):
                intent["time_focus"] = "week"
            elif any(word in query_lower for word in ["month", "monthly"]):
                intent["time_focus"] = "month"
            elif any(
                word in query_lower for word in ["trend", "over time", "historical"]
            ):
                intent["time_focus"] = "historical"

            # Extract aggregation type
            if any(word in query_lower for word in ["average", "avg", "mean"]):
                intent["aggregation"] = "average"
            elif any(word in query_lower for word in ["total", "sum"]):
                intent["aggregation"] = "total"
            elif any(word in query_lower for word in ["max", "maximum", "highest"]):
                intent["aggregation"] = "maximum"
            elif any(word in query_lower for word in ["min", "minimum", "lowest"]):
                intent["aggregation"] = "minimum"

            # Extract platform/job type filters
            platform_match = re.search(r"platform\s+(\w+)", query_lower)
            if platform_match:
                intent["filters"]["platform"] = platform_match.group(1)

            job_type_match = re.search(r"(\w+)\s+jobs?", query_lower)
            if job_type_match:
                intent["filters"]["job_type"] = job_type_match.group(1)

            return intent

        except Exception as e:
            logger.error(f"Error parsing query intent: {e}")
            return {"type": "general", "metrics": [], "filters": {}}

    async def _gather_analysis_data(
        self,
        scope: str,
        entity_id: Optional[str],
        time_range_days: int,
        analysis_intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Gather relevant data for analysis.

        Args:
            scope: Analysis scope
            entity_id: Specific entity ID
            time_range_days: Time range
            analysis_intent: Parsed intent

        Returns:
            Gathered data dictionary
        """
        try:
            data = {"entities": [], "jobs": [], "platforms": [], "instances": []}

            # Gather data based on scope
            if scope in ["all", "job"] or entity_id:
                # Get jobs
                jobs = await self.iss_client.get_jobs(
                    platform_id=analysis_intent["filters"].get("platform"), limit=200
                )

                # Get detailed job information
                detailed_jobs = []
                for job in jobs[:50]:  # Limit for performance
                    try:
                        if job.job_id:
                            detail = await self.iss_client.get_job(job.job_id)
                            detailed_jobs.append(detail)
                    except Exception:
                        continue

                data["jobs"] = detailed_jobs

            if scope in ["all", "platform"]:
                # Get platforms
                platforms = await self.iss_client.get_platforms(limit=50)
                data["platforms"] = platforms

            if scope in ["all", "instance"]:
                # Get instances
                instances = await self.iss_client.get_instances(
                    platform_id=analysis_intent["filters"].get("platform"), limit=100
                )
                data["instances"] = instances

            # Filter by specific entity if provided
            if entity_id:
                if scope == "job":
                    data["jobs"] = [j for j in data["jobs"] if j.job_id == entity_id]
                elif scope == "platform":
                    data["platforms"] = [
                        p for p in data["platforms"] if p.platform_id == entity_id
                    ]
                elif scope == "instance":
                    data["instances"] = [
                        i for i in data["instances"] if i.instance_id == entity_id
                    ]

            data["entities"] = data["jobs"] + data["platforms"] + data["instances"]

            return data

        except Exception as e:
            logger.error(f"Error gathering analysis data: {e}")
            return {"entities": [], "jobs": [], "platforms": [], "instances": []}

    async def _perform_custom_analysis(
        self, query: str, analysis_intent: Dict[str, Any], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform analysis based on intent and data.

        Args:
            query: Original query
            analysis_intent: Parsed intent
            data: Gathered data

        Returns:
            Analysis results
        """
        try:
            results = {}
            analysis_type = analysis_intent["type"]

            if analysis_type == "performance":
                results = await self._analyze_performance_custom(data, analysis_intent)
            elif analysis_type == "resource":
                results = await self._analyze_resource_custom(data, analysis_intent)
            elif analysis_type == "reliability":
                results = await self._analyze_reliability_custom(data, analysis_intent)
            elif analysis_type == "trend":
                results = await self._analyze_trend_custom(data, analysis_intent)
            elif analysis_type == "comparison":
                results = await self._analyze_comparison_custom(data, analysis_intent)
            else:
                results = await self._analyze_general_custom(data, analysis_intent)

            return results

        except Exception as e:
            logger.error(f"Error performing custom analysis: {e}")
            return {"error": str(e)}

    async def _analyze_performance_custom(
        self, data: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze performance metrics."""
        jobs = data.get("jobs", [])
        completed_jobs = [
            j
            for j in jobs
            if j.status.value == "Completed" and j.actual_runtime_minutes
        ]

        if not completed_jobs:
            return {"message": "No completed jobs found for performance analysis"}

        runtimes = [j.actual_runtime_minutes for j in completed_jobs]

        import statistics

        results = {
            "job_count": len(completed_jobs),
            "avg_runtime": statistics.mean(runtimes),
            "min_runtime": min(runtimes),
            "max_runtime": max(runtimes),
            "median_runtime": statistics.median(runtimes),
        }

        if "cpu" in intent["metrics"]:
            cpu_usages = [
                j.peak_cpu_usage_percent
                for j in completed_jobs
                if j.peak_cpu_usage_percent
            ]
            if cpu_usages:
                results["avg_cpu_usage"] = statistics.mean(cpu_usages)

        return results

    async def _analyze_resource_custom(
        self, data: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze resource utilization."""
        jobs = data.get("jobs", [])
        instances = data.get("instances", [])

        results = {}

        # Job resource analysis
        if jobs:
            cpu_usages = [
                j.peak_cpu_usage_percent for j in jobs if j.peak_cpu_usage_percent
            ]
            memory_usages = [
                j.peak_memory_usage_gb for j in jobs if j.peak_memory_usage_gb
            ]

            if cpu_usages:
                import statistics

                results["job_cpu_avg"] = statistics.mean(cpu_usages)
                results["job_cpu_max"] = max(cpu_usages)

            if memory_usages:
                import statistics

                results["job_memory_avg"] = statistics.mean(memory_usages)
                results["job_memory_max"] = max(memory_usages)

        # Instance resource analysis
        if instances:
            active_instances = [i for i in instances if i.is_active]
            results["total_instances"] = len(instances)
            results["active_instances"] = len(active_instances)

            if active_instances:
                cpu_utils = [
                    i.current_cpu_usage_percent
                    for i in active_instances
                    if i.current_cpu_usage_percent
                ]
                if cpu_utils:
                    import statistics

                    results["instance_cpu_avg"] = statistics.mean(cpu_utils)

        return results

    async def _analyze_reliability_custom(
        self, data: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze reliability metrics."""
        jobs = data.get("jobs", [])

        if not jobs:
            return {"message": "No jobs found for reliability analysis"}

        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j.status.value == "Completed"])
        failed_jobs = len([j for j in jobs if j.status.value == "Failed"])

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": (
                (completed_jobs / total_jobs) * 100 if total_jobs > 0 else 0
            ),
            "failure_rate": (failed_jobs / total_jobs) * 100 if total_jobs > 0 else 0,
        }

    async def _analyze_trend_custom(
        self, data: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze trends (simplified)."""
        jobs = data.get("jobs", [])

        if len(jobs) < 5:
            return {"message": "Insufficient data for trend analysis"}

        # Sort by creation date
        sorted_jobs = sorted(
            [j for j in jobs if j.created_at], key=lambda x: x.created_at
        )

        # Simple trend calculation (first half vs second half)
        mid_point = len(sorted_jobs) // 2
        first_half = sorted_jobs[:mid_point]
        second_half = sorted_jobs[mid_point:]

        first_success_rate = (
            len([j for j in first_half if j.status.value == "Completed"])
            / len(first_half)
            * 100
        )
        second_success_rate = (
            len([j for j in second_half if j.status.value == "Completed"])
            / len(second_half)
            * 100
        )

        return {
            "early_period_success_rate": first_success_rate,
            "recent_period_success_rate": second_success_rate,
            "trend_direction": (
                "improving" if second_success_rate > first_success_rate else "declining"
            ),
        }

    async def _analyze_comparison_custom(
        self, data: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze comparisons between entities."""
        platforms = data.get("platforms", [])

        if len(platforms) < 2:
            return {"message": "Need at least 2 platforms for comparison"}

        # Simple platform comparison
        comparisons = []
        for platform in platforms[:5]:  # Limit comparisons
            comparison = {
                "platform_id": platform.platform_id,
                "platform_name": platform.name,
                "is_available": platform.is_available,
                "max_cpu": platform.max_cpu_count,
                "max_memory": platform.max_memory_gb,
            }
            comparisons.append(comparison)

        return {"platform_comparisons": comparisons}

    async def _analyze_general_custom(
        self, data: Dict[str, Any], intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """General analysis for unspecified queries."""
        results = {
            "summary": {
                "total_jobs": len(data.get("jobs", [])),
                "total_platforms": len(data.get("platforms", [])),
                "total_instances": len(data.get("instances", [])),
            }
        }

        jobs = data.get("jobs", [])
        if jobs:
            completed = len([j for j in jobs if j.status.value == "Completed"])
            results["summary"]["completed_jobs"] = completed
            results["summary"]["success_rate"] = (
                (completed / len(jobs)) * 100 if jobs else 0
            )

        return results

    async def _generate_custom_summary(
        self, query: str, analysis_results: Dict[str, Any]
    ) -> Tuple[str, List[str]]:
        """Generate summary for custom analysis."""
        try:
            if "error" in analysis_results:
                return f"Analysis failed: {analysis_results['error']}", []

            if "message" in analysis_results:
                return analysis_results["message"], []

            # Generate summary based on results
            summary_parts = []
            key_findings = []

            if "job_count" in analysis_results:
                summary_parts.append(f"Analyzed {analysis_results['job_count']} jobs")

            if "avg_runtime" in analysis_results:
                summary_parts.append(
                    f"Average runtime: {analysis_results['avg_runtime']:.1f} minutes"
                )

            if "success_rate" in analysis_results:
                success_rate = analysis_results["success_rate"]
                summary_parts.append(f"Success rate: {success_rate:.1f}%")

                if success_rate > 95:
                    key_findings.append("Excellent reliability performance")
                elif success_rate < 80:
                    key_findings.append("Poor reliability - requires investigation")

            if "trend_direction" in analysis_results:
                direction = analysis_results["trend_direction"]
                key_findings.append(f"Performance trend is {direction}")

            summary = (
                "Custom analysis completed. " + ". ".join(summary_parts)
                if summary_parts
                else "Analysis completed."
            )

            return summary, key_findings

        except Exception as e:
            logger.error(f"Error generating custom summary: {e}")
            return "Custom analysis completed", []

    async def _generate_custom_recommendations(
        self, analysis_intent: Dict[str, Any], analysis_results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for custom analysis."""
        recommendations = []

        try:
            analysis_type = analysis_intent.get("type", "general")

            if analysis_type == "performance":
                if (
                    "avg_runtime" in analysis_results
                    and analysis_results["avg_runtime"] > 60
                ):
                    recommendations.append(
                        "Consider job optimization - runtime is high"
                    )

            elif analysis_type == "reliability":
                if (
                    "success_rate" in analysis_results
                    and analysis_results["success_rate"] < 90
                ):
                    recommendations.append(
                        "Investigate job failures to improve reliability"
                    )

            elif analysis_type == "resource":
                if (
                    "job_cpu_avg" in analysis_results
                    and analysis_results["job_cpu_avg"] < 40
                ):
                    recommendations.append(
                        "CPU utilization is low - consider resource optimization"
                    )

            # General recommendations
            if not recommendations:
                recommendations.append(
                    "Continue monitoring for optimization opportunities"
                )
                recommendations.append(
                    "Consider detailed analysis for specific improvement areas"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error generating custom recommendations: {e}")
            return ["Review analysis results for optimization opportunities"]

    async def _generate_ai_custom_analysis(
        self,
        query: str,
        analysis_intent: Dict[str, Any],
        analysis_results: Dict[str, Any],
    ) -> Tuple[Optional[str], Optional[float]]:
        """Generate AI analysis for custom query."""
        try:
            analysis_parts = []

            # Query interpretation
            analysis_type = analysis_intent.get("type", "general")
            analysis_parts.append(
                f"QUERY INTERPRETATION: {analysis_type.title()} analysis requested."
            )

            # Results assessment
            if "success_rate" in analysis_results:
                success_rate = analysis_results["success_rate"]
                if success_rate > 90:
                    analysis_parts.append(
                        "PERFORMANCE: Good reliability metrics detected."
                    )
                else:
                    analysis_parts.append(
                        "PERFORMANCE: Reliability issues require attention."
                    )

            if "avg_runtime" in analysis_results:
                analysis_parts.append(
                    "EFFICIENCY: Runtime analysis completed with metrics available."
                )

            # Data quality assessment
            if "job_count" in analysis_results:
                job_count = analysis_results["job_count"]
                if job_count > 20:
                    analysis_parts.append(
                        "DATA QUALITY: Sufficient data for reliable analysis."
                    )
                else:
                    analysis_parts.append(
                        "DATA QUALITY: Limited data - results may vary."
                    )

            ai_analysis = " ".join(analysis_parts)
            confidence_score = 0.7  # Base confidence for custom analysis

            return ai_analysis, confidence_score

        except Exception as e:
            logger.error(f"Error generating AI custom analysis: {e}")
            return None, None
