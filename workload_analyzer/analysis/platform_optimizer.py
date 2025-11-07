"""Platform optimization analysis module."""

import logging
import statistics
from typing import Any, Dict, List, Optional, Tuple

from ..config import Settings
from ..exceptions import AnalysisError
from ..models.platform_models import Instance, Platform
from ..models.response_models import PlatformOptimization
from ..services.iss_client import ISSClient

logger = logging.getLogger(__name__)


class PlatformOptimizer:
    """Analyzer for platform optimization opportunities."""

    def __init__(self, iss_client: ISSClient, settings: Settings):
        """Initialize the platform optimizer.

        Args:
            iss_client: ISS API client
            settings: Application settings
        """
        self.iss_client = iss_client
        self.settings = settings

    async def analyze_optimization(
        self,
        platform_id: Optional[str] = None,
        include_all_platforms: bool = False,
        optimization_goal: str = "performance",
        include_ai_analysis: bool = True,
    ) -> Dict[str, Any]:
        """Analyze platform optimization opportunities.

        Args:
            platform_id: Specific platform to analyze
            include_all_platforms: Analyze all platforms
            optimization_goal: Goal for optimization (performance, cost, utilization)
            include_ai_analysis: Include AI-generated recommendations

        Returns:
            Optimization analysis results
        """
        try:
            logger.info(
                f"Starting platform optimization: platform={platform_id}, goal={optimization_goal}"
            )

            # Get platforms for analysis
            platforms = await self._get_platforms_for_analysis(
                platform_id, include_all_platforms
            )

            if not platforms:
                raise AnalysisError("No platforms found for optimization analysis")

            # Analyze each platform
            optimizations = []
            for platform in platforms:
                optimization = await self._analyze_single_platform(
                    platform, optimization_goal
                )
                if optimization:
                    optimizations.append(optimization)

            # Generate summary and findings
            summary, key_findings = await self._generate_optimization_summary(
                optimizations, optimization_goal
            )

            # Generate recommendations
            recommendations = await self._generate_optimization_recommendations(
                optimizations, optimization_goal
            )

            # Generate AI analysis if requested
            ai_analysis = None
            confidence_score = None
            if include_ai_analysis:
                ai_analysis, confidence_score = (
                    await self._generate_ai_optimization_analysis(
                        platforms, optimizations, optimization_goal
                    )
                )

            return {
                "optimizations": [opt.model_dump() for opt in optimizations],
                "summary": summary,
                "key_findings": key_findings,
                "recommendations": recommendations,
                "ai_analysis": ai_analysis,
                "confidence_score": confidence_score,
                "platform_count": len(platforms),
            }

        except Exception as e:
            logger.error(f"Error in platform optimization analysis: {e}")
            raise AnalysisError(f"Platform optimization failed: {e}")

    async def _get_platforms_for_analysis(
        self, platform_id: Optional[str], include_all_platforms: bool
    ) -> List[Platform]:
        """Get platforms for optimization analysis.

        Args:
            platform_id: Specific platform ID
            include_all_platforms: Include all platforms

        Returns:
            List of platforms
        """
        try:
            if platform_id:
                # Get specific platform
                platform = await self.iss_client.get_platform(platform_id)
                return [platform]
            elif include_all_platforms:
                # Get all available platforms
                platforms = await self.iss_client.get_platforms(
                    is_available=True, limit=100
                )
                return platforms
            else:
                raise AnalysisError(
                    "Must specify platform_id or include_all_platforms=True"
                )

        except Exception as e:
            logger.error(f"Error getting platforms for analysis: {e}")
            raise AnalysisError(f"Failed to retrieve platforms: {e}")

    async def _analyze_single_platform(
        self, platform: Platform, optimization_goal: str
    ) -> Optional[PlatformOptimization]:
        """Analyze optimization for a single platform.

        Args:
            platform: Platform to analyze
            optimization_goal: Optimization goal

        Returns:
            Platform optimization analysis
        """
        try:
            # Get platform instances and recent jobs
            instances = await self.iss_client.get_instances(
                platform_id=platform.platform_id, limit=100
            )

            recent_jobs = await self.iss_client.get_jobs(
                platform_id=platform.platform_id, limit=50
            )

            # Calculate utilization metrics
            utilization_data = self._calculate_platform_utilization(
                instances, recent_jobs
            )

            # Generate optimization recommendations based on goal
            recommendations = self._generate_platform_recommendations(
                platform, instances, recent_jobs, utilization_data, optimization_goal
            )

            # Calculate resource adjustments
            resource_adjustments = self._calculate_resource_adjustments(
                platform, instances, utilization_data, optimization_goal
            )

            # Estimate impact
            impact_estimation = self._estimate_optimization_impact(
                platform, utilization_data, recommendations, optimization_goal
            )

            return PlatformOptimization(
                platform_id=platform.platform_id,
                platform_name=platform.name,
                current_utilization_percent=utilization_data.get("utilization_percent"),
                avg_job_runtime_minutes=utilization_data.get("avg_runtime_minutes"),
                queue_depth=utilization_data.get("queue_depth"),
                recommended_actions=recommendations,
                resource_adjustments=resource_adjustments,
                configuration_changes=self._suggest_configuration_changes(
                    platform, utilization_data
                ),
                estimated_performance_improvement_percent=impact_estimation.get(
                    "performance_improvement"
                ),
                estimated_cost_impact=impact_estimation.get("cost_impact"),
                implementation_effort=impact_estimation.get("effort"),
            )

        except Exception as e:
            logger.error(f"Error analyzing platform {platform.platform_id}: {e}")
            return None

    def _calculate_platform_utilization(
        self, instances: List[Instance], recent_jobs: List[Any]
    ) -> Dict[str, Any]:
        """Calculate platform utilization metrics.

        Args:
            instances: Platform instances
            recent_jobs: Recent jobs on platform

        Returns:
            Utilization metrics
        """
        try:
            if not instances:
                return {"utilization_percent": 0}

            # Instance utilization
            total_instances = len(instances)
            active_instances = len([i for i in instances if i.is_active])
            in_use_instances = len([i for i in instances if i.in_use])

            utilization_percent = (
                (in_use_instances / total_instances * 100) if total_instances > 0 else 0
            )

            # CPU utilization
            cpu_usages = [
                i.current_cpu_usage_percent
                for i in instances
                if i.current_cpu_usage_percent
            ]
            avg_cpu_utilization = statistics.mean(cpu_usages) if cpu_usages else 0

            # Memory utilization
            memory_utilizations = []
            for instance in instances:
                if instance.allocated_memory_gb and instance.current_memory_usage_gb:
                    utilization = (
                        instance.current_memory_usage_gb / instance.allocated_memory_gb
                    ) * 100
                    memory_utilizations.append(utilization)

            avg_memory_utilization = (
                statistics.mean(memory_utilizations) if memory_utilizations else 0
            )

            # Job metrics
            completed_jobs = [
                j
                for j in recent_jobs
                if hasattr(j, "status") and j.status == "Completed"
            ]
            runtimes = []
            for job in completed_jobs:
                if (
                    hasattr(job, "actual_runtime_minutes")
                    and job.actual_runtime_minutes
                ):
                    runtimes.append(job.actual_runtime_minutes)

            avg_runtime_minutes = statistics.mean(runtimes) if runtimes else None

            # Queue depth (simplified estimation)
            pending_jobs = [
                j
                for j in recent_jobs
                if hasattr(j, "status") and j.status in ["Pending", "Queued"]
            ]
            queue_depth = len(pending_jobs)

            return {
                "utilization_percent": utilization_percent,
                "active_instances": active_instances,
                "total_instances": total_instances,
                "avg_cpu_utilization": avg_cpu_utilization,
                "avg_memory_utilization": avg_memory_utilization,
                "avg_runtime_minutes": avg_runtime_minutes,
                "queue_depth": queue_depth,
                "completed_jobs": len(completed_jobs),
                "pending_jobs": len(pending_jobs),
            }

        except Exception as e:
            logger.error(f"Error calculating utilization: {e}")
            return {"utilization_percent": 0}

    def _generate_platform_recommendations(
        self,
        platform: Platform,
        instances: List[Instance],
        recent_jobs: List[Any],
        utilization_data: Dict[str, Any],
        optimization_goal: str,
    ) -> List[str]:
        """Generate platform-specific recommendations.

        Args:
            platform: Platform object
            instances: Platform instances
            recent_jobs: Recent jobs
            utilization_data: Utilization metrics
            optimization_goal: Optimization goal

        Returns:
            List of recommendations
        """
        recommendations = []

        utilization = utilization_data.get("utilization_percent", 0)
        cpu_util = utilization_data.get("avg_cpu_utilization", 0)
        memory_util = utilization_data.get("avg_memory_utilization", 0)
        queue_depth = utilization_data.get("queue_depth", 0)

        if optimization_goal == "performance":
            if utilization > 85:
                recommendations.append(
                    "Add more instances to reduce resource contention"
                )
            if cpu_util > 80:
                recommendations.append(
                    "Increase CPU allocation or optimize workload distribution"
                )
            if memory_util > 80:
                recommendations.append("Increase memory allocation to prevent swapping")
            if queue_depth > 10:
                recommendations.append(
                    "Scale up platform capacity to reduce job queue wait times"
                )

        elif optimization_goal == "cost":
            if utilization < 30:
                recommendations.append(
                    "Consider reducing instance count to lower costs"
                )
            if cpu_util < 40:
                recommendations.append("Downsize CPU allocation to match actual usage")
            if memory_util < 40:
                recommendations.append("Optimize memory allocation to reduce waste")
            if utilization_data.get("pending_jobs", 0) == 0:
                recommendations.append(
                    "Consider scaling down during low-demand periods"
                )

        elif optimization_goal == "utilization":
            if utilization < 60:
                recommendations.append(
                    "Improve workload scheduling to increase utilization"
                )
            if abs(cpu_util - memory_util) > 30:
                recommendations.append("Balance CPU and memory allocation ratios")
            recommendations.append(
                "Implement dynamic scaling based on workload patterns"
            )

        # General recommendations
        if not instances:
            recommendations.append(
                "Platform has no active instances - investigate configuration"
            )

        if platform.maintenance_mode:
            recommendations.append("Platform is in maintenance mode - review necessity")

        return recommendations

    def _calculate_resource_adjustments(
        self,
        platform: Platform,
        instances: List[Instance],
        utilization_data: Dict[str, Any],
        optimization_goal: str,
    ) -> Dict[str, Any]:
        """Calculate recommended resource adjustments.

        Args:
            platform: Platform object
            instances: Platform instances
            utilization_data: Utilization data
            optimization_goal: Optimization goal

        Returns:
            Resource adjustment recommendations
        """
        adjustments = {}

        if not instances:
            return adjustments

        # Current resource allocation
        total_cpu = sum(i.allocated_cpu_count or 0 for i in instances)
        total_memory = sum(i.allocated_memory_gb or 0 for i in instances)

        utilization = utilization_data.get("utilization_percent", 0)
        cpu_util = utilization_data.get("avg_cpu_utilization", 0)
        memory_util = utilization_data.get("avg_memory_utilization", 0)

        if optimization_goal == "performance":
            if utilization > 80:
                adjustments["instance_count"] = (
                    f"Increase by {max(1, len(instances) // 4)} instances"
                )
            if cpu_util > 75:
                adjustments["cpu_allocation"] = (
                    f"Increase CPU by 25% (from {total_cpu} cores)"
                )
            if memory_util > 75:
                adjustments["memory_allocation"] = (
                    f"Increase memory by 25% (from {total_memory:.1f} GB)"
                )

        elif optimization_goal == "cost":
            if utilization < 40:
                reduction = max(1, len(instances) // 3)
                adjustments["instance_count"] = f"Reduce by {reduction} instances"
            if cpu_util < 50:
                adjustments["cpu_allocation"] = (
                    f"Reduce CPU by 20% (from {total_cpu} cores)"
                )
            if memory_util < 50:
                adjustments["memory_allocation"] = (
                    f"Reduce memory by 20% (from {total_memory:.1f} GB)"
                )

        return adjustments

    def _suggest_configuration_changes(
        self, platform: Platform, utilization_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest configuration changes for the platform.

        Args:
            platform: Platform object
            utilization_data: Utilization data

        Returns:
            Configuration change suggestions
        """
        changes = {}

        # Timeout adjustments
        if utilization_data.get("avg_runtime_minutes"):
            avg_runtime = utilization_data["avg_runtime_minutes"]
            if platform.defaults and platform.defaults.default_timeout_minutes:
                current_timeout = platform.defaults.default_timeout_minutes
                if avg_runtime > current_timeout * 0.8:
                    changes["timeout_minutes"] = int(avg_runtime * 1.5)

        # Concurrent job limits
        utilization = utilization_data.get("utilization_percent", 0)
        if utilization > 90 and platform.max_concurrent_jobs:
            changes["max_concurrent_jobs"] = max(1, platform.max_concurrent_jobs - 2)
        elif utilization < 30 and platform.max_concurrent_jobs:
            changes["max_concurrent_jobs"] = platform.max_concurrent_jobs + 2

        return changes

    def _estimate_optimization_impact(
        self,
        platform: Platform,
        utilization_data: Dict[str, Any],
        recommendations: List[str],
        optimization_goal: str,
    ) -> Dict[str, Any]:
        """Estimate the impact of optimization recommendations.

        Args:
            platform: Platform object
            utilization_data: Utilization data
            recommendations: Generated recommendations
            optimization_goal: Optimization goal

        Returns:
            Impact estimation
        """
        impact = {}

        # Performance improvement estimation
        utilization = utilization_data.get("utilization_percent", 0)
        queue_depth = utilization_data.get("queue_depth", 0)

        if optimization_goal == "performance":
            if utilization > 80:
                impact["performance_improvement"] = 15 + (utilization - 80) * 0.5
            elif queue_depth > 5:
                impact["performance_improvement"] = 10 + queue_depth * 2
            else:
                impact["performance_improvement"] = 5

        elif optimization_goal == "cost":
            if utilization < 50:
                savings = (50 - utilization) * 0.8
                impact["performance_improvement"] = (
                    0  # No performance gain for cost optimization
                )
                impact["cost_savings_percent"] = min(savings, 30)
            else:
                impact["cost_savings_percent"] = 5

        # Cost impact
        if len(recommendations) > 3:
            impact["cost_impact"] = "High"
        elif len(recommendations) > 1:
            impact["cost_impact"] = "Medium"
        else:
            impact["cost_impact"] = "Low"

        # Implementation effort
        complex_changes = [
            r
            for r in recommendations
            if any(
                word in r.lower() for word in ["add", "increase", "scale", "implement"]
            )
        ]
        if len(complex_changes) > 2:
            impact["effort"] = "High"
        elif len(complex_changes) > 0:
            impact["effort"] = "Medium"
        else:
            impact["effort"] = "Low"

        return impact

    async def _generate_optimization_summary(
        self, optimizations: List[PlatformOptimization], optimization_goal: str
    ) -> Tuple[str, List[str]]:
        """Generate optimization summary and key findings.

        Args:
            optimizations: Platform optimizations
            optimization_goal: Optimization goal

        Returns:
            Tuple of (summary, key_findings)
        """
        if not optimizations:
            return "No optimization opportunities found", []

        # Calculate aggregate metrics
        avg_utilization = statistics.mean(
            [o.current_utilization_percent or 0 for o in optimizations]
        )
        total_platforms = len(optimizations)

        # Generate summary
        summary = (
            f"Analyzed {total_platforms} platforms for {optimization_goal} optimization. "
            f"Average utilization is {avg_utilization:.1f}%. "
            f"Found {sum(len(o.recommended_actions) for o in optimizations)} optimization opportunities."
        )

        # Generate key findings
        key_findings = []

        underutilized = [
            o for o in optimizations if (o.current_utilization_percent or 0) < 40
        ]
        if underutilized:
            key_findings.append(
                f"{len(underutilized)} platforms are underutilized (< 40%)"
            )

        overutilized = [
            o for o in optimizations if (o.current_utilization_percent or 0) > 85
        ]
        if overutilized:
            key_findings.append(
                f"{len(overutilized)} platforms are overutilized (> 85%)"
            )

        high_impact = [
            o
            for o in optimizations
            if (o.estimated_performance_improvement_percent or 0) > 20
        ]
        if high_impact:
            key_findings.append(
                f"{len(high_impact)} platforms have high optimization potential (> 20% improvement)"
            )

        return summary, key_findings

    async def _generate_optimization_recommendations(
        self, optimizations: List[PlatformOptimization], optimization_goal: str
    ) -> List[str]:
        """Generate overall optimization recommendations.

        Args:
            optimizations: Platform optimizations
            optimization_goal: Optimization goal

        Returns:
            List of recommendations
        """
        recommendations = []

        if not optimizations:
            return ["No platforms available for optimization"]

        # Priority recommendations based on goal
        if optimization_goal == "performance":
            recommendations.append(
                "Focus on overutilized platforms first to reduce bottlenecks"
            )
            recommendations.append(
                "Implement auto-scaling for dynamic workload adjustment"
            )

        elif optimization_goal == "cost":
            recommendations.append(
                "Consolidate underutilized platforms to reduce costs"
            )
            recommendations.append(
                "Implement scheduled scaling for predictable workloads"
            )

        elif optimization_goal == "utilization":
            recommendations.append("Balance workload distribution across platforms")
            recommendations.append(
                "Optimize resource allocation based on actual usage patterns"
            )

        # Specific recommendations
        high_queue = [o for o in optimizations if (o.queue_depth or 0) > 10]
        if high_queue:
            recommendations.append(
                "Address high queue depths to improve job wait times"
            )

        low_efficiency = [
            o for o in optimizations if (o.current_utilization_percent or 0) < 30
        ]
        if low_efficiency:
            recommendations.append(
                "Review low-efficiency platforms for consolidation opportunities"
            )

        return recommendations

    async def _generate_ai_optimization_analysis(
        self,
        platforms: List[Platform],
        optimizations: List[PlatformOptimization],
        optimization_goal: str,
    ) -> Tuple[Optional[str], Optional[float]]:
        """Generate AI-powered optimization analysis.

        Args:
            platforms: Platform data
            optimizations: Optimization results
            optimization_goal: Optimization goal

        Returns:
            Tuple of (ai_analysis, confidence_score)
        """
        try:
            # Generate structured AI analysis
            analysis_parts = []

            avg_util = statistics.mean(
                [o.current_utilization_percent or 0 for o in optimizations]
            )
            total_improvements = sum(
                o.estimated_performance_improvement_percent or 0 for o in optimizations
            )

            # Overall assessment
            if avg_util > 80:
                analysis_parts.append(
                    "CAPACITY ASSESSMENT: Critical - Multiple platforms approaching capacity limits."
                )
            elif avg_util > 60:
                analysis_parts.append(
                    "CAPACITY ASSESSMENT: Moderate - Some platforms nearing optimal utilization."
                )
            else:
                analysis_parts.append(
                    "CAPACITY ASSESSMENT: Good - Platforms have available capacity for growth."
                )

            # Optimization potential
            if total_improvements > 50:
                analysis_parts.append(
                    "OPTIMIZATION POTENTIAL: High - Significant performance gains achievable."
                )
            elif total_improvements > 20:
                analysis_parts.append(
                    "OPTIMIZATION POTENTIAL: Moderate - Meaningful improvements possible."
                )
            else:
                analysis_parts.append(
                    "OPTIMIZATION POTENTIAL: Low - Platforms are well-optimized."
                )

            # Implementation priority
            high_impact_count = len(
                [
                    o
                    for o in optimizations
                    if (o.estimated_performance_improvement_percent or 0) > 15
                ]
            )
            if high_impact_count > 2:
                analysis_parts.append(
                    "IMPLEMENTATION: Prioritize high-impact platforms for immediate optimization."
                )
            else:
                analysis_parts.append(
                    "IMPLEMENTATION: Gradual optimization approach recommended."
                )

            ai_analysis = " ".join(analysis_parts)
            confidence_score = min(0.7 + (len(optimizations) * 0.05), 0.95)

            return ai_analysis, confidence_score

        except Exception as e:
            logger.error(f"Error generating AI optimization analysis: {e}")
            return None, None

    async def recommend_optimal_platform(
        self, job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend the optimal platform for a job.

        Args:
            job_requirements: Job requirements including CPU, memory, etc.

        Returns:
            Platform recommendation with alternatives
        """
        try:
            # Get available platforms
            platforms_response = await self.iss_client.get_platforms()
            platforms = platforms_response.get("platforms", [])

            if not platforms:
                raise AnalysisError("No platforms available for recommendation")

            # Score each platform for the job requirements
            scored_platforms = []
            for platform in platforms:
                if isinstance(platform, dict):
                    platform_data = platform
                else:
                    platform_data = (
                        platform.model_dump()
                        if hasattr(platform, "model_dump")
                        else platform.dict()
                    )

                score = self._calculate_platform_score(platform_data, job_requirements)
                scored_platforms.append(
                    {
                        "platform_id": platform_data.get("platform_id"),
                        "score": score,
                        "platform_data": platform_data,
                    }
                )

            # Sort by score (highest first)
            scored_platforms.sort(key=lambda x: x["score"], reverse=True)

            recommended = scored_platforms[0] if scored_platforms else None
            alternatives = scored_platforms[1:4] if len(scored_platforms) > 1 else []

            return {
                "recommended_platform": (
                    {
                        "platform_id": recommended["platform_id"],
                        "optimization_score": recommended["score"],
                        "platform_details": recommended["platform_data"],
                    }
                    if recommended
                    else None
                ),
                "alternatives": [
                    {
                        "platform_id": alt["platform_id"],
                        "optimization_score": alt["score"],
                        "platform_details": alt["platform_data"],
                    }
                    for alt in alternatives
                ],
                "optimization_score": recommended["score"] if recommended else 0,
                "job_requirements": job_requirements,
            }

        except Exception as e:
            logger.error(f"Error recommending optimal platform: {e}")
            raise AnalysisError(f"Failed to recommend optimal platform: {e}")

    async def analyze_platform_utilization(self, platform_id: str) -> Dict[str, Any]:
        """Analyze platform utilization and capacity.

        Args:
            platform_id: Platform to analyze

        Returns:
            Platform utilization analysis
        """
        try:
            # Get platform details
            platform_data = await self.iss_client.get_platform_detail(platform_id)

            # Get running jobs on this platform
            jobs_response = await self.iss_client.get_jobs(
                platform_filter=platform_id, status_filter="running"
            )
            running_jobs = jobs_response.get("jobs", [])

            # Calculate current utilization
            total_cpu = platform_data.get("max_cpu_count", 0)
            total_memory = platform_data.get("max_memory_gb", 0.0)
            max_jobs = platform_data.get("max_concurrent_jobs", 0)

            used_cpu = sum(job.get("allocated_cpu_count", 0) for job in running_jobs)
            used_memory = sum(
                job.get("allocated_memory_gb", 0.0) for job in running_jobs
            )
            current_jobs = len(running_jobs)

            cpu_utilization = (used_cpu / total_cpu * 100) if total_cpu > 0 else 0
            memory_utilization = (
                (used_memory / total_memory * 100) if total_memory > 0 else 0
            )
            job_utilization = (current_jobs / max_jobs * 100) if max_jobs > 0 else 0

            # Analyze capacity
            remaining_cpu = max(0, total_cpu - used_cpu)
            remaining_memory = max(0.0, total_memory - used_memory)
            remaining_job_slots = max(0, max_jobs - current_jobs)

            # Generate optimization opportunities
            opportunities = []
            if cpu_utilization < 50:
                opportunities.append(
                    "CPU utilization is low - consider consolidating workloads"
                )
            if memory_utilization < 50:
                opportunities.append(
                    "Memory utilization is low - optimize memory allocation"
                )
            if job_utilization < 30:
                opportunities.append(
                    "Job slots underutilized - increase job throughput"
                )
            if cpu_utilization > 90:
                opportunities.append(
                    "CPU near capacity - consider workload redistribution"
                )
            if memory_utilization > 90:
                opportunities.append("Memory near capacity - reduce memory usage")

            return {
                "platform_id": platform_id,
                "current_utilization": {
                    "cpu_percent": round(cpu_utilization, 2),
                    "memory_percent": round(memory_utilization, 2),
                    "job_slots_percent": round(job_utilization, 2),
                    "running_jobs": current_jobs,
                },
                "capacity_analysis": {
                    "total_capacity": {
                        "cpu_count": total_cpu,
                        "memory_gb": total_memory,
                        "max_jobs": max_jobs,
                    },
                    "available_capacity": {
                        "cpu_count": remaining_cpu,
                        "memory_gb": remaining_memory,
                        "job_slots": remaining_job_slots,
                    },
                },
                "optimization_opportunities": opportunities,
                "efficiency_score": round(
                    (100 - abs(75 - cpu_utilization) - abs(75 - memory_utilization))
                    / 2,
                    2,
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing platform utilization: {e}")
            raise AnalysisError(f"Failed to analyze platform utilization: {e}")

    async def optimize_job_placement(
        self, jobs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Optimize job placement across available platforms.

        Args:
            jobs: List of jobs to place

        Returns:
            Job placement recommendations
        """
        try:
            # Get available platforms
            platforms_response = await self.iss_client.get_platforms()
            platforms = platforms_response.get("platforms", [])

            if not platforms:
                raise AnalysisError("No platforms available for job placement")

            placement_recommendations = []

            for job in jobs:
                # Convert job to requirements format
                job_requirements = {
                    "cpu_count": job.get("cpu_count", 1),
                    "memory_gb": job.get("memory_gb", 1.0),
                    "priority": job.get("priority", 5),
                    "job_type": job.get("job_type", "unknown"),
                }

                # Find best platform for this job
                best_score = 0
                best_platform = None

                for platform in platforms:
                    if isinstance(platform, dict):
                        platform_data = platform
                    else:
                        platform_data = (
                            platform.model_dump()
                            if hasattr(platform, "model_dump")
                            else platform.dict()
                        )

                    score = self._calculate_platform_score(
                        platform_data, job_requirements
                    )
                    if score > best_score:
                        best_score = score
                        best_platform = platform_data

                placement_recommendations.append(
                    {
                        "job_id": job.get("job_id"),
                        "recommended_platform": (
                            best_platform.get("platform_id") if best_platform else None
                        ),
                        "placement_score": best_score,
                        "job_requirements": job_requirements,
                        "platform_details": best_platform,
                    }
                )

            # Generate optimization summary
            placed_jobs = len(
                [r for r in placement_recommendations if r["recommended_platform"]]
            )
            average_score = (
                statistics.mean(
                    [r["placement_score"] for r in placement_recommendations]
                )
                if placement_recommendations
                else 0
            )

            platform_usage = {}
            for rec in placement_recommendations:
                if rec["recommended_platform"]:
                    platform_id = rec["recommended_platform"]
                    platform_usage[platform_id] = platform_usage.get(platform_id, 0) + 1

            return {
                "placement_recommendations": placement_recommendations,
                "optimization_summary": {
                    "total_jobs": len(jobs),
                    "successfully_placed": placed_jobs,
                    "average_placement_score": round(average_score, 2),
                    "platform_distribution": platform_usage,
                    "optimization_quality": (
                        "high"
                        if average_score > 75
                        else "medium" if average_score > 50 else "low"
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error optimizing job placement: {e}")
            raise AnalysisError(f"Failed to optimize job placement: {e}")

    def _calculate_platform_score(
        self, platform_data: Dict[str, Any], job_requirements: Dict[str, Any]
    ) -> float:
        """Calculate platform suitability score for job requirements.

        Args:
            platform_data: Platform specifications
            job_requirements: Job resource requirements

        Returns:
            Suitability score (0-100)
        """
        try:
            score = 0.0

            # Resource availability scoring (40 points max)
            max_cpu = platform_data.get("max_cpu_count", 1)
            max_memory = platform_data.get("max_memory_gb", 1.0)
            required_cpu = job_requirements.get("cpu_count", 1)
            required_memory = job_requirements.get("memory_gb", 1.0)

            # CPU scoring
            if max_cpu >= required_cpu:
                cpu_ratio = required_cpu / max_cpu
                score += 20 * (
                    1 - abs(0.7 - cpu_ratio)
                )  # Optimal around 70% utilization

            # Memory scoring
            if max_memory >= required_memory:
                memory_ratio = required_memory / max_memory
                score += 20 * (
                    1 - abs(0.7 - memory_ratio)
                )  # Optimal around 70% utilization

            # Current utilization scoring (30 points max)
            current_util = platform_data.get("current_utilization_percent", 50.0)
            # Prefer platforms with moderate utilization (60-80%)
            if 60 <= current_util <= 80:
                score += 30
            elif 40 <= current_util < 60 or 80 < current_util <= 90:
                score += 20
            else:
                score += 10

            # Platform type compatibility (20 points max)
            platform_type = platform_data.get("platform_type", "").lower()
            job_type = job_requirements.get("job_type", "").lower()

            if platform_type == "simulation" and "simulation" in job_type:
                score += 20
            elif platform_type in ["compute", "general"] and job_type in [
                "iwps",
                "compute",
            ]:
                score += 15
            else:
                score += 10

            # Capacity scoring (10 points max)
            max_jobs = platform_data.get("max_concurrent_jobs", 1)
            if max_jobs > 10:
                score += 10
            elif max_jobs > 5:
                score += 7
            else:
                score += 5

            return min(100.0, max(0.0, score))

        except Exception as e:
            logger.error(f"Error calculating platform score: {e}")
            return 0.0
