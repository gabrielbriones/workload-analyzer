"""Job insights analysis module."""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..config import Settings
from ..exceptions import AnalysisError
from ..models.job_models import JobDetail, JobRequest, JobStatus, JobType
from ..models.response_models import JobInsights
from ..services.iss_client import ISSClient

logger = logging.getLogger(__name__)


class JobInsightsAnalyzer:
    """Analyzer for individual job insights and recommendations."""

    def __init__(self, iss_client: ISSClient, settings: Settings):
        """Initialize the job insights analyzer."""
        self.iss_client = iss_client
        self.settings = settings

    async def analyze_job_insights(
        self,
        job_id: str,
        compare_similar: bool = True,
        include_predictions: bool = True,
        include_ai_analysis: bool = True,
    ) -> Dict[str, Any]:
        """Analyze job insights and recommendations.

        Args:
            job_id: Job to analyze
            compare_similar: Compare with similar jobs
            include_predictions: Include performance predictions
            include_ai_analysis: Include AI insights

        Returns:
            Job insights analysis
        """
        try:
            logger.info(f"Analyzing job insights for {job_id}")

            # Get job details
            job = await self.iss_client.get_job(job_id)

            # Get similar jobs for comparison
            similar_jobs = []
            if compare_similar:
                similar_jobs = await self._get_similar_jobs(job)

            # Generate job insights
            insights = await self._generate_job_insights(
                job, similar_jobs, include_predictions
            )

            # Generate summary and findings
            summary, key_findings = await self._generate_insights_summary(job, insights)

            # Generate recommendations
            recommendations = await self._generate_job_recommendations(
                job, similar_jobs, insights
            )

            # Generate AI analysis
            ai_analysis = None
            confidence_score = None
            if include_ai_analysis:
                ai_analysis, confidence_score = await self._generate_ai_insights(
                    job, similar_jobs, insights
                )

            return {
                "insights": [insights.model_dump()],
                "summary": summary,
                "key_findings": key_findings,
                "recommendations": recommendations,
                "ai_analysis": ai_analysis,
                "confidence_score": confidence_score,
                "similar_jobs_count": len(similar_jobs),
            }

        except Exception as e:
            logger.error(f"Error in job insights analysis: {e}")
            raise AnalysisError(f"Job insights analysis failed: {e}")

    async def _get_similar_jobs(self, job: JobDetail) -> List[JobDetail]:
        """Get similar jobs for comparison."""
        try:
            # Get jobs with same type and platform
            similar = await self.iss_client.get_jobs(
                job_type=job.job_type, platform_id=job.platform_id, limit=50
            )

            # Get detailed information for completed jobs
            detailed_similar = []
            for similar_job in similar:
                if similar_job.job_id and similar_job.job_id != job.job_id:
                    try:
                        detail = await self.iss_client.get_job(similar_job.job_id)
                        if detail.status == JobStatus.COMPLETED:
                            detailed_similar.append(detail)

                        if len(detailed_similar) >= 20:  # Limit for performance
                            break
                    except Exception as e:
                        logger.warning(f"Failed to get details for similar job: {e}")
                        continue

            return detailed_similar

        except Exception as e:
            logger.error(f"Error getting similar jobs: {e}")
            return []

    async def _generate_job_insights(
        self, job: JobDetail, similar_jobs: List[JobDetail], include_predictions: bool
    ) -> JobInsights:
        """Generate insights for the job."""
        try:
            # Performance scoring
            performance_score = self._calculate_performance_score(job, similar_jobs)

            # Efficiency rating
            efficiency_rating = self._calculate_efficiency_rating(job, similar_jobs)

            # Identify bottlenecks
            bottlenecks = self._identify_bottlenecks(job)

            # Resource analysis
            resource_utilization = self._analyze_resource_utilization(job)
            resource_recommendations = self._generate_resource_recommendations(
                job, similar_jobs
            )

            # Comparative analysis
            performance_percentile = self._calculate_performance_percentile(
                job, similar_jobs
            )
            improvement_suggestions = self._generate_improvement_suggestions(
                job, similar_jobs
            )

            # Predictions
            estimated_runtime = None
            success_probability = None
            if include_predictions:
                estimated_runtime = self._predict_next_runtime(job, similar_jobs)
                success_probability = self._predict_success_probability(
                    job, similar_jobs
                )

            return JobInsights(
                job_id=job.job_id or "",
                job_name=job.name,
                job_type=job.job_type.value,
                performance_score=performance_score,
                efficiency_rating=efficiency_rating,
                bottlenecks=bottlenecks,
                resource_utilization=resource_utilization,
                resource_recommendations=resource_recommendations,
                similar_jobs_count=len(similar_jobs),
                performance_percentile=performance_percentile,
                improvement_suggestions=improvement_suggestions,
                estimated_next_runtime_minutes=estimated_runtime,
                success_probability_percent=success_probability,
            )

        except Exception as e:
            logger.error(f"Error generating job insights: {e}")
            raise AnalysisError(f"Failed to generate insights: {e}")

    def _calculate_performance_score(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> float:
        """Calculate performance score (0-10)."""
        try:
            score = 5.0  # Base score

            # Runtime performance
            if job.actual_runtime_minutes and similar_jobs:
                similar_runtimes = [
                    j.actual_runtime_minutes
                    for j in similar_jobs
                    if j.actual_runtime_minutes
                ]
                if similar_runtimes:
                    avg_runtime = statistics.mean(similar_runtimes)
                    if job.actual_runtime_minutes < avg_runtime * 0.8:
                        score += 2.0  # Faster than average
                    elif job.actual_runtime_minutes > avg_runtime * 1.5:
                        score -= 2.0  # Slower than average

            # Resource efficiency
            if job.peak_cpu_usage_percent:
                if job.peak_cpu_usage_percent > 80:
                    score += 1.0  # Good CPU utilization
                elif job.peak_cpu_usage_percent < 30:
                    score -= 1.0  # Poor CPU utilization

            # Success status
            if job.status == JobStatus.COMPLETED:
                score += 1.0
            elif job.status == JobStatus.FAILED:
                score -= 3.0

            return max(0.0, min(10.0, score))

        except Exception:
            return 5.0

    def _calculate_efficiency_rating(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> str:
        """Calculate efficiency rating."""
        score = self._calculate_performance_score(job, similar_jobs)

        if score >= 8:
            return "Excellent"
        elif score >= 6:
            return "Good"
        elif score >= 4:
            return "Fair"
        else:
            return "Poor"

    def _identify_bottlenecks(self, job: JobDetail) -> List[str]:
        """Identify potential bottlenecks."""
        bottlenecks = []

        if job.peak_cpu_usage_percent and job.peak_cpu_usage_percent > 95:
            bottlenecks.append("CPU bottleneck - usage near 100%")

        if job.peak_memory_usage_gb and job.actual_allocation:
            if (
                job.actual_allocation.memory_gb
                and job.peak_memory_usage_gb > job.actual_allocation.memory_gb * 0.9
            ):
                bottlenecks.append("Memory bottleneck - near allocation limit")

        if job.actual_runtime_minutes and job.max_runtime_minutes:
            if job.actual_runtime_minutes > job.max_runtime_minutes * 0.8:
                bottlenecks.append("Time constraint - approaching timeout")

        if job.status == JobStatus.FAILED and job.error_message:
            if "timeout" in job.error_message.lower():
                bottlenecks.append("Timeout bottleneck")
            elif "memory" in job.error_message.lower():
                bottlenecks.append("Memory allocation bottleneck")
            elif "disk" in job.error_message.lower():
                bottlenecks.append("Disk space bottleneck")

        return bottlenecks

    def _analyze_resource_utilization(self, job: JobDetail) -> Dict[str, float]:
        """Analyze resource utilization."""
        utilization = {}

        if job.peak_cpu_usage_percent:
            utilization["cpu_percent"] = job.peak_cpu_usage_percent

        if (
            job.peak_memory_usage_gb
            and job.actual_allocation
            and job.actual_allocation.memory_gb
        ):
            utilization["memory_percent"] = (
                job.peak_memory_usage_gb / job.actual_allocation.memory_gb
            ) * 100

        if job.actual_runtime_minutes and job.max_runtime_minutes:
            utilization["time_percent"] = (
                job.actual_runtime_minutes / job.max_runtime_minutes
            ) * 100

        return utilization

    def _generate_resource_recommendations(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> List[str]:
        """Generate resource optimization recommendations."""
        recommendations = []

        # CPU recommendations
        if job.peak_cpu_usage_percent:
            if job.peak_cpu_usage_percent < 30:
                recommendations.append("Reduce CPU allocation - current usage is low")
            elif job.peak_cpu_usage_percent > 90:
                recommendations.append(
                    "Increase CPU allocation - high utilization detected"
                )

        # Memory recommendations
        if (
            job.peak_memory_usage_gb
            and job.actual_allocation
            and job.actual_allocation.memory_gb
        ):
            memory_ratio = job.peak_memory_usage_gb / job.actual_allocation.memory_gb
            if memory_ratio < 0.4:
                recommendations.append(
                    "Reduce memory allocation - current usage is low"
                )
            elif memory_ratio > 0.9:
                recommendations.append("Increase memory allocation - near limit")

        # Runtime recommendations
        if job.actual_runtime_minutes and similar_jobs:
            similar_runtimes = [
                j.actual_runtime_minutes
                for j in similar_jobs
                if j.actual_runtime_minutes
            ]
            if similar_runtimes:
                avg_runtime = statistics.mean(similar_runtimes)
                if job.actual_runtime_minutes > avg_runtime * 2:
                    recommendations.append(
                        "Investigate performance issues - runtime significantly above average"
                    )

        return recommendations

    def _calculate_performance_percentile(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> float:
        """Calculate performance percentile compared to similar jobs."""
        if not similar_jobs or not job.actual_runtime_minutes:
            return 50.0

        similar_runtimes = [
            j.actual_runtime_minutes for j in similar_jobs if j.actual_runtime_minutes
        ]
        if not similar_runtimes:
            return 50.0

        # Lower runtime = better performance = higher percentile
        better_count = len(
            [r for r in similar_runtimes if r > job.actual_runtime_minutes]
        )
        percentile = (better_count / len(similar_runtimes)) * 100

        return percentile

    def _generate_improvement_suggestions(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if job.status == JobStatus.FAILED:
            suggestions.append("Investigate failure cause and implement error handling")

        if job.peak_cpu_usage_percent and job.peak_cpu_usage_percent < 50:
            suggestions.append(
                "Optimize code to better utilize available CPU resources"
            )

        if similar_jobs:
            avg_runtime = statistics.mean(
                [
                    j.actual_runtime_minutes
                    for j in similar_jobs
                    if j.actual_runtime_minutes
                ]
            )
            if (
                job.actual_runtime_minutes
                and job.actual_runtime_minutes > avg_runtime * 1.5
            ):
                suggestions.append(
                    "Profile application to identify performance bottlenecks"
                )

        return suggestions

    def _predict_next_runtime(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> Optional[float]:
        """Predict next runtime based on historical data."""
        if not similar_jobs:
            return job.actual_runtime_minutes

        runtimes = [
            j.actual_runtime_minutes for j in similar_jobs if j.actual_runtime_minutes
        ]
        if not runtimes:
            return job.actual_runtime_minutes

        # Use median for more robust prediction
        return statistics.median(runtimes)

    def _predict_success_probability(
        self, job: JobDetail, similar_jobs: List[JobDetail]
    ) -> Optional[float]:
        """Predict success probability."""
        if not similar_jobs:
            return None

        successful = len([j for j in similar_jobs if j.status == JobStatus.COMPLETED])
        total = len(similar_jobs)

        return (successful / total) * 100 if total > 0 else None

    async def _generate_insights_summary(
        self, job: JobDetail, insights: JobInsights
    ) -> Tuple[str, List[str]]:
        """Generate insights summary."""
        summary = (
            f"Job {job.name} ({job.job_type.value}) achieved {insights.efficiency_rating.lower()} "
            f"performance with score {insights.performance_score:.1f}/10."
        )

        key_findings = []

        if insights.performance_percentile and insights.performance_percentile > 80:
            key_findings.append(
                f"Excellent performance - top {100-insights.performance_percentile:.0f}% of similar jobs"
            )
        elif insights.performance_percentile and insights.performance_percentile < 20:
            key_findings.append(
                f"Below-average performance - bottom {insights.performance_percentile:.0f}% of similar jobs"
            )

        if insights.bottlenecks:
            key_findings.append(
                f"Identified {len(insights.bottlenecks)} bottlenecks requiring attention"
            )

        if insights.resource_recommendations:
            key_findings.append("Resource optimization opportunities available")

        return summary, key_findings

    async def _generate_job_recommendations(
        self, job: JobDetail, similar_jobs: List[JobDetail], insights: JobInsights
    ) -> List[str]:
        """Generate job-specific recommendations."""
        recommendations = []

        # Add resource recommendations
        recommendations.extend(insights.resource_recommendations)

        # Add improvement suggestions
        recommendations.extend(insights.improvement_suggestions)

        # Performance-based recommendations
        if insights.performance_score < 5:
            recommendations.append(
                "Consider job optimization or alternative approaches"
            )

        if insights.bottlenecks:
            recommendations.append(
                "Address identified bottlenecks to improve performance"
            )

        return recommendations

    async def _generate_ai_insights(
        self, job: JobDetail, similar_jobs: List[JobDetail], insights: JobInsights
    ) -> Tuple[Optional[str], Optional[float]]:
        """Generate AI-powered insights."""
        try:
            analysis_parts = []

            # Performance analysis
            if insights.performance_score >= 8:
                analysis_parts.append(
                    "PERFORMANCE: Excellent - Job shows optimal execution characteristics."
                )
            elif insights.performance_score >= 6:
                analysis_parts.append(
                    "PERFORMANCE: Good - Minor optimization opportunities exist."
                )
            else:
                analysis_parts.append(
                    "PERFORMANCE: Needs improvement - Significant optimization potential."
                )

            # Resource analysis
            if insights.resource_recommendations:
                analysis_parts.append(
                    "RESOURCES: Optimization needed - Resource allocation can be improved."
                )
            else:
                analysis_parts.append(
                    "RESOURCES: Well-balanced - Current allocation is appropriate."
                )

            # Comparative analysis
            if insights.performance_percentile and insights.performance_percentile > 75:
                analysis_parts.append(
                    "COMPARISON: Above average - Performs better than most similar jobs."
                )
            elif (
                insights.performance_percentile and insights.performance_percentile < 25
            ):
                analysis_parts.append(
                    "COMPARISON: Below average - Underperforms compared to similar jobs."
                )

            ai_analysis = " ".join(analysis_parts)
            confidence_score = 0.8 if len(similar_jobs) > 10 else 0.6

            return ai_analysis, confidence_score

        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return None, None

    async def generate_job_insights(self, job_id: str) -> Dict[str, Any]:
        """Generate comprehensive insights for a specific job.

        Args:
            job_id: Job ID to analyze

        Returns:
            Job insights data
        """
        try:
            # Get job details
            job_data = await self.iss_client.get_job_detail(job_id)

            if isinstance(job_data, dict):
                job = JobDetail(**job_data)
            else:
                job = job_data

            # Generate basic insights
            insights = []
            patterns = []
            recommendations = []

            # Performance insights
            if hasattr(job, "actual_runtime_minutes") and job.actual_runtime_minutes:
                runtime_hours = job.actual_runtime_minutes / 60
                if runtime_hours > 24:
                    insights.append(
                        f"Long-running job: {runtime_hours:.1f} hours execution time"
                    )
                    recommendations.append(
                        "Consider optimizing algorithms or increasing resources"
                    )
                elif runtime_hours < 0.5:
                    insights.append(
                        f"Quick execution: {job.actual_runtime_minutes} minutes"
                    )
                    patterns.append("fast_execution")

            # Resource insights
            if hasattr(job, "cpu_count") and job.cpu_count:
                if job.cpu_count >= 32:
                    insights.append(f"High CPU usage: {job.cpu_count} cores allocated")
                    patterns.append("high_cpu")
                elif job.cpu_count <= 4:
                    insights.append(f"Low CPU usage: {job.cpu_count} cores allocated")
                    patterns.append("low_cpu")

            # Memory insights
            if hasattr(job, "memory_gb") and job.memory_gb:
                if job.memory_gb >= 64:
                    insights.append(f"High memory allocation: {job.memory_gb} GB")
                    patterns.append("high_memory")
                elif job.memory_gb <= 8:
                    insights.append(f"Low memory allocation: {job.memory_gb} GB")
                    patterns.append("low_memory")

            # Status insights
            if hasattr(job, "status"):
                if job.status == JobStatus.FAILED:
                    insights.append("Job failed - requires investigation")
                    recommendations.append("Review error logs and adjust configuration")
                elif job.status == JobStatus.COMPLETED:
                    insights.append("Job completed successfully")
                    patterns.append("successful_completion")

            # Platform insights
            if hasattr(job, "platform_id") and job.platform_id:
                insights.append(f"Executed on platform: {job.platform_id}")
                patterns.append(f"platform_{job.platform_id.lower()}")

            # Job type insights
            if hasattr(job, "job_type") and job.job_type:
                insights.append(f"Job type: {job.job_type}")
                patterns.append(f"type_{job.job_type.lower()}")

                if job.job_type == JobType.IWPS:
                    recommendations.append(
                        "IWPS jobs benefit from high memory allocation"
                    )
                elif job.job_type == JobType.SIMULATION:
                    recommendations.append(
                        "Simulation jobs typically require balanced CPU/memory"
                    )

            return {
                "job_id": job_id,
                "insights": insights,
                "patterns": patterns,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating job insights for {job_id}: {e}")
            raise AnalysisError(f"Failed to generate job insights: {e}")

    async def identify_failure_patterns(
        self, limit: int = 100, days: int = 30
    ) -> Dict[str, Any]:
        """Identify common failure patterns across jobs.

        Args:
            limit: Maximum number of failed jobs to analyze
            days: Number of days to look back

        Returns:
            Failure pattern analysis
        """
        try:
            # Get recent failed jobs
            since_date = datetime.now() - timedelta(days=days)
            jobs_response = await self.iss_client.get_jobs(
                status_filter="failed", limit=limit, since=since_date.isoformat()
            )

            failed_jobs = jobs_response.get("jobs", [])

            if not failed_jobs:
                return {
                    "failure_patterns": [],
                    "common_causes": ["No recent failures found"],
                    "recommendations": ["System appears stable"],
                }

            # Analyze failure patterns
            error_messages = []
            memory_failures = 0
            timeout_failures = 0
            platform_failures = {}
            job_type_failures = {}

            for job in failed_jobs:
                # Collect error messages
                error_msg = job.get("error_message", "").lower()
                if error_msg:
                    error_messages.append(error_msg)

                # Categorize failures
                if "memory" in error_msg or "oom" in error_msg:
                    memory_failures += 1
                if "timeout" in error_msg or "time" in error_msg:
                    timeout_failures += 1

                # Platform failures
                platform = job.get("platform_id", "unknown")
                platform_failures[platform] = platform_failures.get(platform, 0) + 1

                # Job type failures
                job_type = job.get("job_type", "unknown")
                job_type_failures[job_type] = job_type_failures.get(job_type, 0) + 1

            # Identify common causes
            common_causes = []
            total_failures = len(failed_jobs)

            if memory_failures > total_failures * 0.3:
                common_causes.append(
                    f"Memory allocation issues ({memory_failures} of {total_failures} failures)"
                )

            if timeout_failures > total_failures * 0.2:
                common_causes.append(
                    f"Timeout issues ({timeout_failures} of {total_failures} failures)"
                )

            # Most problematic platform
            if platform_failures:
                worst_platform = max(platform_failures, key=platform_failures.get)
                if platform_failures[worst_platform] > total_failures * 0.4:
                    common_causes.append(
                        f"Platform {worst_platform} issues ({platform_failures[worst_platform]} failures)"
                    )

            # Most problematic job type
            if job_type_failures:
                worst_job_type = max(job_type_failures, key=job_type_failures.get)
                if job_type_failures[worst_job_type] > total_failures * 0.3:
                    common_causes.append(
                        f"{worst_job_type} job type issues ({job_type_failures[worst_job_type]} failures)"
                    )

            # Generate recommendations
            recommendations = []
            if memory_failures > 0:
                recommendations.append(
                    "Review memory allocation policies and increase default memory limits"
                )
            if timeout_failures > 0:
                recommendations.append(
                    "Optimize job timeouts and check for performance bottlenecks"
                )
            if len(platform_failures) > 1:
                recommendations.append(
                    "Distribute workload more evenly across platforms"
                )
            if not common_causes:
                recommendations.append(
                    "Monitor individual job configurations for optimization opportunities"
                )

            failure_patterns = []
            if memory_failures > 0:
                failure_patterns.append(
                    {
                        "type": "memory_allocation",
                        "frequency": memory_failures,
                        "percentage": round(memory_failures / total_failures * 100, 1),
                    }
                )

            if timeout_failures > 0:
                failure_patterns.append(
                    {
                        "type": "timeout",
                        "frequency": timeout_failures,
                        "percentage": round(timeout_failures / total_failures * 100, 1),
                    }
                )

            return {
                "failure_patterns": failure_patterns,
                "common_causes": (
                    common_causes if common_causes else ["Various isolated failures"]
                ),
                "recommendations": recommendations,
                "total_failures_analyzed": total_failures,
                "analysis_period_days": days,
                "platform_distribution": platform_failures,
                "job_type_distribution": job_type_failures,
            }

        except Exception as e:
            logger.error(f"Error identifying failure patterns: {e}")
            raise AnalysisError(f"Failed to identify failure patterns: {e}")

    async def analyze_job_dependencies(self, limit: int = 200) -> Dict[str, Any]:
        """Analyze job dependencies and workflow patterns.

        Args:
            limit: Maximum number of jobs to analyze

        Returns:
            Job dependency analysis
        """
        try:
            # Get recent jobs
            jobs_response = await self.iss_client.get_jobs(limit=limit)
            jobs = jobs_response.get("jobs", [])

            if not jobs:
                return {"dependency_graph": {}, "critical_path": [], "bottlenecks": []}

            # Build dependency graph
            dependency_graph = {}
            job_details = {}

            for job in jobs:
                job_id = job.get("job_id")
                if not job_id:
                    continue

                job_details[job_id] = job
                dependencies = job.get("dependencies", [])

                if isinstance(dependencies, str):
                    dependencies = [dependencies] if dependencies else []
                elif not isinstance(dependencies, list):
                    dependencies = []

                dependency_graph[job_id] = {
                    "dependencies": dependencies,
                    "name": job.get("name", job_id),
                    "status": job.get("status", "unknown"),
                    "runtime_minutes": job.get("runtime_minutes", 0),
                }

            # Find critical path (longest dependency chain)
            critical_path = self._find_critical_path(dependency_graph)

            # Identify bottlenecks
            bottlenecks = self._identify_bottlenecks(dependency_graph, job_details)

            # Calculate dependency metrics
            total_jobs = len(dependency_graph)
            jobs_with_deps = len(
                [j for j in dependency_graph.values() if j["dependencies"]]
            )
            max_dependencies = (
                max(len(j["dependencies"]) for j in dependency_graph.values())
                if dependency_graph
                else 0
            )

            return {
                "dependency_graph": dependency_graph,
                "critical_path": critical_path,
                "bottlenecks": bottlenecks,
                "metrics": {
                    "total_jobs": total_jobs,
                    "jobs_with_dependencies": jobs_with_deps,
                    "dependency_percentage": (
                        round(jobs_with_deps / total_jobs * 100, 1)
                        if total_jobs > 0
                        else 0
                    ),
                    "max_dependencies_per_job": max_dependencies,
                    "critical_path_length": len(critical_path),
                },
            }

        except Exception as e:
            logger.error(f"Error analyzing job dependencies: {e}")
            raise AnalysisError(f"Failed to analyze job dependencies: {e}")

    def _find_critical_path(self, dependency_graph: Dict[str, Any]) -> List[str]:
        """Find the critical path (longest dependency chain)."""
        try:

            def get_path_length(job_id: str, visited: set) -> int:
                if job_id in visited:
                    return 0  # Circular dependency, break cycle

                visited.add(job_id)
                job_info = dependency_graph.get(job_id, {})
                dependencies = job_info.get("dependencies", [])

                if not dependencies:
                    visited.remove(job_id)
                    return 1

                max_dep_length = 0
                for dep in dependencies:
                    if dep in dependency_graph:
                        dep_length = get_path_length(dep, visited)
                        max_dep_length = max(max_dep_length, dep_length)

                visited.remove(job_id)
                return max_dep_length + 1

            # Find job with longest path
            longest_path_job = None
            longest_path_length = 0

            for job_id in dependency_graph:
                path_length = get_path_length(job_id, set())
                if path_length > longest_path_length:
                    longest_path_length = path_length
                    longest_path_job = job_id

            # Build the actual path
            if longest_path_job:
                path = []
                current = longest_path_job
                visited = set()

                while current and current not in visited:
                    path.append(current)
                    visited.add(current)
                    dependencies = dependency_graph.get(current, {}).get(
                        "dependencies", []
                    )
                    current = dependencies[0] if dependencies else None

                return list(reversed(path))

            return []

        except Exception as e:
            logger.error(f"Error finding critical path: {e}")
            return []

    def _identify_bottlenecks(
        self, dependency_graph: Dict[str, Any], job_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify potential bottlenecks in the workflow."""
        try:
            bottlenecks = []

            # Jobs that many other jobs depend on
            dependency_count = {}
            for job_id, job_info in dependency_graph.items():
                for dep in job_info.get("dependencies", []):
                    dependency_count[dep] = dependency_count.get(dep, 0) + 1

            # Find jobs with high dependency count
            for job_id, count in dependency_count.items():
                if count >= 3:  # Threshold for bottleneck
                    job_info = dependency_graph.get(job_id, {})
                    bottlenecks.append(
                        {
                            "job_id": job_id,
                            "job_name": job_info.get("name", job_id),
                            "dependent_jobs_count": count,
                            "status": job_info.get("status", "unknown"),
                            "type": "high_dependency",
                            "impact": "high" if count >= 5 else "medium",
                        }
                    )

            # Long-running jobs that block others
            for job_id, job_info in dependency_graph.items():
                runtime = job_info.get("runtime_minutes", 0)
                if (
                    runtime > 120 and dependency_count.get(job_id, 0) > 0
                ):  # 2+ hour jobs that others depend on
                    bottlenecks.append(
                        {
                            "job_id": job_id,
                            "job_name": job_info.get("name", job_id),
                            "runtime_minutes": runtime,
                            "dependent_jobs_count": dependency_count.get(job_id, 0),
                            "type": "long_running",
                            "impact": (
                                "high" if runtime > 360 else "medium"
                            ),  # 6+ hours is high impact
                        }
                    )

            return bottlenecks

        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")
            return []
