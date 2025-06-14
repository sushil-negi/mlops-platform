"""
Visualization API endpoints for Experiment Tracking service
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class VisualizationType(str):
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    BOX_PLOT = "box_plot"
    HISTOGRAM = "histogram"
    PARALLEL_COORDINATES = "parallel_coordinates"
    CONFUSION_MATRIX = "confusion_matrix"


class VisualizationRequest(BaseModel):
    """Visualization request model"""

    visualization_type: str = Field(..., description="Type of visualization")
    experiment_ids: Optional[List[uuid.UUID]] = Field(
        None, description="Experiment IDs to visualize"
    )
    run_ids: Optional[List[uuid.UUID]] = Field(None, description="Run IDs to visualize")
    metrics: List[str] = Field(..., description="Metrics to visualize")

    # Configuration
    title: Optional[str] = Field(None, description="Chart title")
    x_axis: Optional[str] = Field(None, description="X-axis metric")
    y_axis: Optional[str] = Field(None, description="Y-axis metric")
    group_by: Optional[str] = Field(None, description="Grouping parameter")

    # Filtering
    time_range: Optional[Dict[str, datetime]] = Field(
        None, description="Time range filter"
    )
    parameter_filters: Optional[Dict[str, Any]] = Field(
        None, description="Parameter filters"
    )

    # Styling
    theme: str = Field(default="plotly_white", description="Chart theme")
    width: int = Field(default=800, description="Chart width")
    height: int = Field(default=600, description="Chart height")


class VisualizationResponse(BaseModel):
    """Visualization response model"""

    id: uuid.UUID
    visualization_type: str
    title: str

    # Chart data
    chart_data: Dict[str, Any] = Field(..., description="Plotly chart data")
    chart_layout: Dict[str, Any] = Field(..., description="Plotly chart layout")

    # Metadata
    created_at: datetime
    experiment_count: int
    run_count: int
    metric_count: int

    # URLs
    static_url: Optional[str] = Field(None, description="Static image URL")
    interactive_url: Optional[str] = Field(None, description="Interactive chart URL")
    export_url: Optional[str] = Field(None, description="Data export URL")


class DashboardRequest(BaseModel):
    """Dashboard request model"""

    name: str = Field(..., description="Dashboard name")
    project_id: Optional[uuid.UUID] = Field(None, description="Project ID")
    experiment_ids: Optional[List[uuid.UUID]] = Field(
        None, description="Experiment IDs"
    )

    # Layout
    layout: str = Field(default="grid", description="Dashboard layout")
    columns: int = Field(default=2, description="Number of columns")

    # Widgets
    widgets: List[Dict[str, Any]] = Field(..., description="Dashboard widgets")


class DashboardResponse(BaseModel):
    """Dashboard response model"""

    id: uuid.UUID
    name: str
    project_id: Optional[uuid.UUID]

    # Layout
    layout: str
    columns: int
    widgets: List[Dict[str, Any]]

    # Metadata
    created_at: datetime
    updated_at: datetime

    # URLs
    dashboard_url: str
    embed_url: str


@router.post("/charts", response_model=VisualizationResponse)
async def create_visualization(
    viz_request: VisualizationRequest,
) -> VisualizationResponse:
    """Create a new visualization"""

    viz_id = uuid.uuid4()

    # Mock chart data generation based on visualization type
    if viz_request.visualization_type == VisualizationType.LINE_CHART:
        chart_data = {
            "data": [
                {
                    "x": [1, 2, 3, 4, 5],
                    "y": [0.85, 0.90, 0.92, 0.95, 0.97],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Accuracy",
                    "line": {"color": "blue"},
                },
                {
                    "x": [1, 2, 3, 4, 5],
                    "y": [0.82, 0.87, 0.89, 0.93, 0.96],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "F1 Score",
                    "line": {"color": "red"},
                },
            ]
        }

        chart_layout = {
            "title": viz_request.title or "Metric Trends Over Time",
            "xaxis": {"title": viz_request.x_axis or "Epoch"},
            "yaxis": {"title": viz_request.y_axis or "Score"},
            "template": viz_request.theme,
            "width": viz_request.width,
            "height": viz_request.height,
        }

    elif viz_request.visualization_type == VisualizationType.BAR_CHART:
        chart_data = {
            "data": [
                {
                    "x": ["Experiment 1", "Experiment 2", "Experiment 3"],
                    "y": [0.95, 0.92, 0.97],
                    "type": "bar",
                    "name": "Accuracy",
                    "marker": {"color": "skyblue"},
                }
            ]
        }

        chart_layout = {
            "title": viz_request.title or "Experiment Comparison",
            "xaxis": {"title": "Experiments"},
            "yaxis": {"title": "Accuracy"},
            "template": viz_request.theme,
            "width": viz_request.width,
            "height": viz_request.height,
        }

    elif viz_request.visualization_type == VisualizationType.CONFUSION_MATRIX:
        chart_data = {
            "data": [
                {
                    "z": [[85, 2, 1], [3, 90, 2], [1, 1, 88]],
                    "type": "heatmap",
                    "colorscale": "Blues",
                    "showscale": True,
                }
            ]
        }

        chart_layout = {
            "title": viz_request.title or "Confusion Matrix",
            "xaxis": {"title": "Predicted"},
            "yaxis": {"title": "Actual"},
            "template": viz_request.theme,
            "width": viz_request.width,
            "height": viz_request.height,
        }

    else:
        # Default to scatter plot
        chart_data = {
            "data": [
                {
                    "x": [0.001, 0.01, 0.1],
                    "y": [0.85, 0.92, 0.89],
                    "type": "scatter",
                    "mode": "markers",
                    "name": "Learning Rate vs Accuracy",
                    "marker": {"size": 10},
                }
            ]
        }

        chart_layout = {
            "title": viz_request.title or "Parameter vs Metric",
            "xaxis": {"title": viz_request.x_axis or "Parameter"},
            "yaxis": {"title": viz_request.y_axis or "Metric"},
            "template": viz_request.theme,
            "width": viz_request.width,
            "height": viz_request.height,
        }

    # Create response
    visualization = VisualizationResponse(
        id=viz_id,
        visualization_type=viz_request.visualization_type,
        title=str(chart_layout["title"]),
        chart_data=chart_data,
        chart_layout=chart_layout,
        created_at=datetime.utcnow(),
        experiment_count=len(viz_request.experiment_ids or []),
        run_count=len(viz_request.run_ids or []),
        metric_count=len(viz_request.metrics),
        static_url=f"/api/v1/visualizations/charts/{viz_id}/static.png",
        interactive_url=f"/api/v1/visualizations/charts/{viz_id}/interactive",
        export_url=f"/api/v1/visualizations/charts/{viz_id}/export",
    )

    logger.info(f"Created visualization {viz_id}: {visualization.title}")

    return visualization


@router.get("/charts/{chart_id}", response_model=VisualizationResponse)
async def get_visualization(chart_id: uuid.UUID) -> VisualizationResponse:
    """Get visualization by ID"""

    # Mock response (replace with actual database lookup)
    visualization = VisualizationResponse(
        id=chart_id,
        visualization_type=VisualizationType.LINE_CHART,
        title="Sample Visualization",
        chart_data={
            "data": [
                {
                    "x": [1, 2, 3, 4, 5],
                    "y": [0.85, 0.90, 0.92, 0.95, 0.97],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Accuracy",
                }
            ]
        },
        chart_layout={
            "title": "Sample Visualization",
            "xaxis": {"title": "Epoch"},
            "yaxis": {"title": "Score"},
        },
        created_at=datetime.utcnow(),
        experiment_count=1,
        run_count=5,
        metric_count=1,
        static_url=f"/api/v1/visualizations/charts/{chart_id}/static.png",
        interactive_url=f"/api/v1/visualizations/charts/{chart_id}/interactive",
        export_url=f"/api/v1/visualizations/charts/{chart_id}/export",
    )

    return visualization


@router.get("/templates")
async def get_visualization_templates():
    """Get available visualization templates"""

    templates = {
        "metric_comparison": {
            "name": "Metric Comparison",
            "description": "Compare metrics across experiments",
            "type": VisualizationType.BAR_CHART,
            "required_metrics": ["accuracy"],
            "optional_metrics": ["f1_score", "precision", "recall"],
        },
        "training_progress": {
            "name": "Training Progress",
            "description": "Show metric trends over epochs",
            "type": VisualizationType.LINE_CHART,
            "required_metrics": ["loss"],
            "optional_metrics": ["accuracy", "val_loss", "val_accuracy"],
        },
        "hyperparameter_search": {
            "name": "Hyperparameter Search",
            "description": "Visualize hyperparameter optimization",
            "type": VisualizationType.SCATTER_PLOT,
            "required_metrics": ["accuracy"],
            "parameters": ["learning_rate", "batch_size"],
        },
        "model_performance_matrix": {
            "name": "Model Performance Matrix",
            "description": "Confusion matrix for classification",
            "type": VisualizationType.CONFUSION_MATRIX,
            "required_metrics": ["predictions", "labels"],
        },
        "healthcare_metrics_dashboard": {
            "name": "Healthcare Metrics Dashboard",
            "description": "Healthcare-specific performance metrics",
            "type": "dashboard",
            "widgets": [
                {"type": "metric_card", "metric": "crisis_detection_rate"},
                {"type": "line_chart", "metrics": ["accuracy", "f1_score"]},
                {"type": "confusion_matrix", "metric": "predictions"},
                {"type": "bar_chart", "metric": "response_quality_score"},
            ],
        },
    }

    return {"templates": templates, "total": len(templates)}


@router.post(
    "/charts/from-template/{template_name}", response_model=VisualizationResponse
)
async def create_visualization_from_template(
    template_name: str, viz_request: VisualizationRequest
) -> VisualizationResponse:
    """Create visualization from template"""

    templates = (await get_visualization_templates())["templates"]

    if template_name not in templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found",
        )

    template = templates[template_name]

    # Apply template defaults
    viz_request.visualization_type = template.get(
        "type", viz_request.visualization_type
    )
    if not viz_request.title:
        viz_request.title = template["name"]

    return await create_visualization(viz_request)


@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(dashboard_request: DashboardRequest) -> DashboardResponse:
    """Create a new dashboard"""

    dashboard_id = uuid.uuid4()

    dashboard = DashboardResponse(
        id=dashboard_id,
        name=dashboard_request.name,
        project_id=dashboard_request.project_id,
        layout=dashboard_request.layout,
        columns=dashboard_request.columns,
        widgets=dashboard_request.widgets,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        dashboard_url=f"/api/v1/visualizations/dashboards/{dashboard_id}",
        embed_url=f"/api/v1/visualizations/dashboards/{dashboard_id}/embed",
    )

    logger.info(f"Created dashboard {dashboard_id}: {dashboard.name}")

    return dashboard


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: uuid.UUID) -> DashboardResponse:
    """Get dashboard by ID"""

    # Mock response (replace with actual database lookup)
    dashboard = DashboardResponse(
        id=dashboard_id,
        name="Healthcare Metrics Dashboard",
        project_id=None,
        layout="grid",
        columns=2,
        widgets=[
            {
                "type": "metric_card",
                "metric": "accuracy",
                "position": {"row": 0, "col": 0},
            },
            {
                "type": "line_chart",
                "metrics": ["accuracy", "f1_score"],
                "position": {"row": 0, "col": 1},
            },
            {
                "type": "confusion_matrix",
                "metric": "predictions",
                "position": {"row": 1, "col": 0},
            },
            {
                "type": "bar_chart",
                "metric": "crisis_detection_rate",
                "position": {"row": 1, "col": 1},
            },
        ],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        dashboard_url=f"/api/v1/visualizations/dashboards/{dashboard_id}",
        embed_url=f"/api/v1/visualizations/dashboards/{dashboard_id}/embed",
    )

    return dashboard


@router.get("/dashboards")
async def list_dashboards(
    project_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List dashboards"""

    # Mock data (replace with actual database query)
    dashboards = [
        {
            "id": str(uuid.uuid4()),
            "name": "Healthcare Overview",
            "project_id": project_id,
            "widget_count": 6,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Model Performance",
            "project_id": project_id,
            "widget_count": 4,
            "created_at": datetime.utcnow() - timedelta(days=1),
            "updated_at": datetime.utcnow() - timedelta(hours=2),
        },
    ]

    return {
        "dashboards": dashboards,
        "total": len(dashboards),
        "page": page,
        "size": size,
        "total_pages": 1,
    }


@router.get("/export/experiment/{experiment_id}")
async def export_experiment_visualizations(
    experiment_id: uuid.UUID, format: str = "pdf"
):
    """Export all visualizations for an experiment"""

    if format not in ["pdf", "png", "html", "json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported formats: pdf, png, html, json",
        )

    export_url = f"/exports/experiment_{experiment_id}_visualizations.{format}"

    return {
        "message": "Export created successfully",
        "format": format,
        "download_url": export_url,
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
    }


@router.get("/healthcare/crisis-detection-dashboard")
async def get_healthcare_crisis_dashboard():
    """Get healthcare-specific crisis detection dashboard"""

    dashboard_data = {
        "title": "Healthcare Crisis Detection Dashboard",
        "widgets": [
            {
                "type": "metric_card",
                "title": "Crisis Detection Rate",
                "value": 0.9918,
                "target": 0.99,
                "status": "healthy",
                "trend": "up",
            },
            {
                "type": "metric_card",
                "title": "Response Quality Score",
                "value": 0.847,
                "target": 0.8,
                "status": "healthy",
                "trend": "stable",
            },
            {
                "type": "line_chart",
                "title": "Real-time Performance",
                "data": {
                    "timestamps": [
                        "2024-01-15T10:00:00Z",
                        "2024-01-15T11:00:00Z",
                        "2024-01-15T12:00:00Z",
                    ],
                    "crisis_detection_rate": [0.991, 0.993, 0.9918],
                    "accuracy": [0.981, 0.984, 0.982],
                },
            },
            {
                "type": "alert_summary",
                "title": "Recent Alerts",
                "alerts": [
                    {
                        "level": "info",
                        "message": "Model accuracy stable at 98.2%",
                        "time": "2 hours ago",
                    },
                    {
                        "level": "warning",
                        "message": "Response time increased by 15ms",
                        "time": "4 hours ago",
                    },
                ],
            },
        ],
        "last_updated": datetime.utcnow().isoformat(),
        "auto_refresh_seconds": 30,
    }

    return dashboard_data
