"""Analysis API endpoints with AI integration."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status

from ..config import Settings, get_settings
from ..exceptions import (
    AnalysisError,
    ISSAuthenticationError,
    ISSClientError,
)
from ..models.response_models import AnalysisResponse
from ..services.iss_client import ISSClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


async def get_bearer_token(authorization: str = Header(...)) -> str:
    """Extract and validate bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Bearer token
        
    Raises:
        HTTPException: If token format is invalid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
        )
    return authorization[7:]  # Remove "Bearer " prefix


async def get_iss_client(
    bearer_token: str = Depends(get_bearer_token),
    settings: Settings = Depends(get_settings)
) -> ISSClient:
    """Dependency to get ISS client with bearer token."""
    return ISSClient(settings, bearer_token)


@router.get(
    "/performance",
    response_model=AnalysisResponse,
    summary="Performance analysis",
    description="Analyze job and platform performance with AI insights.",
)
async def analyze_performance(
    platform_id: Optional[str] = Query(None, description="Analyze specific platform"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    days: int = Query(7, ge=1, le=90, description="Days of data to analyze"),
    include_ai_analysis: bool = Query(
        True, description="Include AI-generated insights"
    ),
    iss_client: ISSClient = Depends(get_iss_client),
    settings: Settings = Depends(get_settings),
):
    """Perform comprehensive performance analysis."""
    try:
        # Import analysis modules here to avoid circular imports
        from ..analysis.performance_analyzer import PerformanceAnalyzer

        analyzer = PerformanceAnalyzer(iss_client, settings)

        async with iss_client:
            # Perform analysis
            analysis_result = await analyzer.analyze_performance(
                platform_id=platform_id,
                job_type=job_type,
                days=days,
                include_ai_analysis=include_ai_analysis,
            )

        return AnalysisResponse(
            analysis_type="performance",
            generated_at=datetime.utcnow(),
            performance_metrics=analysis_result.get("metrics"),
            summary=analysis_result.get("summary"),
            key_findings=analysis_result.get("key_findings", []),
            recommendations=analysis_result.get("recommendations", []),
            ai_analysis=analysis_result.get("ai_analysis"),
            confidence_score=analysis_result.get("confidence_score"),
            analysis_parameters={
                "platform_id": platform_id,
                "job_type": job_type,
                "days": days,
                "include_ai_analysis": include_ai_analysis,
            },
            data_sources=["ISS API", "Job History", "Platform Metrics"],
        )

    except AnalysisError as e:
        logger.error(f"Analysis error in performance analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error in performance analysis: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error in performance analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in performance analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/platform-optimization",
    response_model=AnalysisResponse,
    summary="Platform optimization",
    description="Analyze platform utilization and provide optimization recommendations.",
)
async def analyze_platform_optimization(
    platform_id: Optional[str] = Query(None, description="Analyze specific platform"),
    include_all_platforms: bool = Query(False, description="Analyze all platforms"),
    optimization_goal: str = Query(
        "performance", description="Optimization goal: performance, cost, utilization"
    ),
    include_ai_analysis: bool = Query(
        True, description="Include AI-generated recommendations"
    ),
    iss_client: ISSClient = Depends(get_iss_client),
    settings: Settings = Depends(get_settings),
):
    """Analyze platform optimization opportunities."""
    try:
        from ..analysis.platform_optimizer import PlatformOptimizer

        optimizer = PlatformOptimizer(iss_client, settings)

        async with iss_client:
            analysis_result = await optimizer.analyze_optimization(
                platform_id=platform_id,
                include_all_platforms=include_all_platforms,
                optimization_goal=optimization_goal,
                include_ai_analysis=include_ai_analysis,
            )

        return AnalysisResponse(
            analysis_type="platform_optimization",
            generated_at=datetime.utcnow(),
            platform_optimizations=analysis_result.get("optimizations", []),
            summary=analysis_result.get("summary"),
            key_findings=analysis_result.get("key_findings", []),
            recommendations=analysis_result.get("recommendations", []),
            ai_analysis=analysis_result.get("ai_analysis"),
            confidence_score=analysis_result.get("confidence_score"),
            analysis_parameters={
                "platform_id": platform_id,
                "include_all_platforms": include_all_platforms,
                "optimization_goal": optimization_goal,
                "include_ai_analysis": include_ai_analysis,
            },
            data_sources=[
                "ISS API",
                "Platform Metrics",
                "Instance Data",
                "Utilization History",
            ],
        )

    except AnalysisError as e:
        logger.error(f"Analysis error in platform optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error in platform optimization: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error in platform optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in platform optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/job-insights/{job_id}",
    response_model=AnalysisResponse,
    summary="Job insights",
    description="Get detailed insights and recommendations for a specific job.",
)
async def analyze_job_insights(
    job_id: str,
    compare_similar: bool = Query(True, description="Compare with similar jobs"),
    include_predictions: bool = Query(
        True, description="Include performance predictions"
    ),
    include_ai_analysis: bool = Query(
        True, description="Include AI-generated insights"
    ),
    iss_client: ISSClient = Depends(get_iss_client),
    settings: Settings = Depends(get_settings),
):
    """Analyze a specific job and provide insights."""
    try:
        from ..analysis.job_insights import JobInsightsAnalyzer

        analyzer = JobInsightsAnalyzer(iss_client, settings)

        async with iss_client:
            analysis_result = await analyzer.analyze_job_insights(
                job_id=job_id,
                compare_similar=compare_similar,
                include_predictions=include_predictions,
                include_ai_analysis=include_ai_analysis,
            )

        return AnalysisResponse(
            analysis_type="job_insights",
            generated_at=datetime.utcnow(),
            job_insights=analysis_result.get("insights", []),
            summary=analysis_result.get("summary"),
            key_findings=analysis_result.get("key_findings", []),
            recommendations=analysis_result.get("recommendations", []),
            ai_analysis=analysis_result.get("ai_analysis"),
            confidence_score=analysis_result.get("confidence_score"),
            analysis_parameters={
                "job_id": job_id,
                "compare_similar": compare_similar,
                "include_predictions": include_predictions,
                "include_ai_analysis": include_ai_analysis,
            },
            data_sources=[
                "ISS API",
                "Job Data",
                "Historical Comparisons",
                "Performance Metrics",
            ],
        )

    except AnalysisError as e:
        logger.error(f"Analysis error in job insights for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error in job insights for {job_id}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error in job insights for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in job insights for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/trends",
    response_model=AnalysisResponse,
    summary="Trend analysis",
    description="Analyze trends in job performance and platform utilization.",
)
async def analyze_trends(
    metric: str = Query(
        "runtime",
        description="Metric to analyze: runtime, success_rate, resource_usage",
    ),
    platform_id: Optional[str] = Query(None, description="Analyze specific platform"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    period: str = Query("week", description="Time period: day, week, month"),
    trend_window: int = Query(
        30, ge=7, le=180, description="Days of data for trend analysis"
    ),
    include_ai_analysis: bool = Query(
        True, description="Include AI trend interpretation"
    ),
    iss_client: ISSClient = Depends(get_iss_client),
    settings: Settings = Depends(get_settings),
):
    """Analyze trends in performance metrics."""
    try:
        from ..analysis.trend_analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer(iss_client, settings)

        async with iss_client:
            analysis_result = await analyzer.analyze_trends(
                metric=metric,
                platform_id=platform_id,
                job_type=job_type,
                period=period,
                trend_window=trend_window,
                include_ai_analysis=include_ai_analysis,
            )

        return AnalysisResponse(
            analysis_type="trends",
            generated_at=datetime.utcnow(),
            summary=analysis_result.get("summary"),
            key_findings=analysis_result.get("key_findings", []),
            recommendations=analysis_result.get("recommendations", []),
            ai_analysis=analysis_result.get("ai_analysis"),
            confidence_score=analysis_result.get("confidence_score"),
            analysis_parameters={
                "metric": metric,
                "platform_id": platform_id,
                "job_type": job_type,
                "period": period,
                "trend_window": trend_window,
                "include_ai_analysis": include_ai_analysis,
            },
            data_sources=["ISS API", "Historical Data", "Time Series Analysis"],
        )

    except AnalysisError as e:
        logger.error(f"Analysis error in trend analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error in trend analysis: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error in trend analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in trend analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/custom",
    response_model=AnalysisResponse,
    summary="Custom analysis",
    description="Perform custom analysis with AI assistance based on natural language queries.",
)
async def custom_analysis(
    query: str = Query(..., description="Natural language analysis query"),
    scope: str = Query(
        "all", description="Analysis scope: job, platform, instance, all"
    ),
    entity_id: Optional[str] = Query(None, description="Specific entity ID to analyze"),
    time_range_days: int = Query(
        30, ge=1, le=365, description="Time range for analysis"
    ),
    include_ai_analysis: bool = Query(True, description="Include AI interpretation"),
    iss_client: ISSClient = Depends(get_iss_client),
    settings: Settings = Depends(get_settings),
):
    """Perform custom analysis based on natural language query."""
    try:
        from ..analysis.custom_analyzer import CustomAnalyzer

        analyzer = CustomAnalyzer(iss_client, settings)

        async with iss_client:
            analysis_result = await analyzer.analyze_custom_query(
                query=query,
                scope=scope,
                entity_id=entity_id,
                time_range_days=time_range_days,
                include_ai_analysis=include_ai_analysis,
            )

        return AnalysisResponse(
            analysis_type="custom",
            generated_at=datetime.utcnow(),
            summary=analysis_result.get("summary"),
            key_findings=analysis_result.get("key_findings", []),
            recommendations=analysis_result.get("recommendations", []),
            ai_analysis=analysis_result.get("ai_analysis"),
            confidence_score=analysis_result.get("confidence_score"),
            analysis_parameters={
                "query": query,
                "scope": scope,
                "entity_id": entity_id,
                "time_range_days": time_range_days,
                "include_ai_analysis": include_ai_analysis,
            },
            data_sources=["ISS API", "Dynamic Query Analysis", "AI Processing"],
        )

    except AnalysisError as e:
        logger.error(f"Analysis error in custom analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except ISSAuthenticationError as e:
        logger.error(f"Authentication error in custom analysis: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ISSClientError as e:
        logger.error(f"ISS client error in custom analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External service error: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in custom analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
