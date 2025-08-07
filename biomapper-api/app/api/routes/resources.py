"""API routes for resource management."""
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ...services.resource_manager import ResourceManager, ResourceStatus
from ..deps import get_resource_manager

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/status")
async def get_resource_status(
    manager: ResourceManager = Depends(get_resource_manager),
) -> Dict[str, Any]:
    """Get status of all managed resources."""
    resources = await manager.get_resource_status()

    # Convert to list of dicts for JSON serialization
    resource_list = []
    for resource in resources.values():
        resource_dict = resource.dict()
        # Convert datetime to string
        resource_dict["last_check"] = resource_dict["last_check"].isoformat()
        resource_list.append(resource_dict)

    return {
        "resources": resource_list,
        "summary": {
            "total": len(resources),
            "healthy": sum(
                1 for r in resources.values() if r.status == ResourceStatus.HEALTHY
            ),
            "degraded": sum(
                1 for r in resources.values() if r.status == ResourceStatus.DEGRADED
            ),
            "unavailable": sum(
                1 for r in resources.values() if r.status == ResourceStatus.UNAVAILABLE
            ),
            "unknown": sum(
                1 for r in resources.values() if r.status == ResourceStatus.UNKNOWN
            ),
        },
    }


@router.get("/status/{resource_name}")
async def get_single_resource_status(
    resource_name: str, manager: ResourceManager = Depends(get_resource_manager)
) -> Dict[str, Any]:
    """Get status of a specific resource."""
    resources = await manager.get_resource_status()

    if resource_name not in resources:
        raise HTTPException(
            status_code=404, detail=f"Resource '{resource_name}' not found"
        )

    resource = resources[resource_name]
    resource_dict = resource.dict()
    resource_dict["last_check"] = resource_dict["last_check"].isoformat()

    return resource_dict


@router.post("/{resource_name}/start")
async def start_resource(
    resource_name: str, manager: ResourceManager = Depends(get_resource_manager)
) -> Dict[str, Any]:
    """Start a specific resource."""
    try:
        success = await manager.start_resource(resource_name)
        resources = await manager.get_resource_status()

        return {
            "success": success,
            "resource": resource_name,
            "status": resources[resource_name].status.value
            if resource_name in resources
            else "unknown",
            "message": "Resource started successfully"
            if success
            else "Failed to start resource",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error starting resource: {str(e)}"
        )


@router.post("/{resource_name}/stop")
async def stop_resource(
    resource_name: str, manager: ResourceManager = Depends(get_resource_manager)
) -> Dict[str, Any]:
    """Stop a specific resource."""
    try:
        success = await manager.stop_resource(resource_name)
        return {
            "success": success,
            "resource": resource_name,
            "message": "Resource stopped successfully"
            if success
            else "Failed to stop resource",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error stopping resource: {str(e)}"
        )


@router.post("/{resource_name}/restart")
async def restart_resource(
    resource_name: str, manager: ResourceManager = Depends(get_resource_manager)
) -> Dict[str, Any]:
    """Restart a specific resource."""
    try:
        # Stop the resource
        await manager.stop_resource(resource_name)

        # Wait a bit
        await asyncio.sleep(2)

        # Start the resource
        success = await manager.start_resource(resource_name)

        return {
            "success": success,
            "resource": resource_name,
            "message": "Resource restarted successfully"
            if success
            else "Failed to restart resource",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error restarting resource: {str(e)}"
        )


@router.post("/{resource_name}/check")
async def check_resource(
    resource_name: str, manager: ResourceManager = Depends(get_resource_manager)
) -> Dict[str, Any]:
    """Manually trigger a health check for a resource."""
    try:
        status = await manager.check_resource(resource_name)
        resources = await manager.get_resource_status()
        resource = resources.get(resource_name)

        return {
            "resource": resource_name,
            "status": status.value,
            "last_check": resource.last_check.isoformat() if resource else None,
            "error_message": resource.error_message if resource else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking resource: {str(e)}"
        )


@router.get("/requirements/{strategy_name}")
async def get_strategy_requirements(
    strategy_name: str, manager: ResourceManager = Depends(get_resource_manager)
) -> Dict[str, Any]:
    """Get resource requirements for a strategy."""
    try:
        # This would need to load the strategy from file or database
        # For now, return a mock response
        from ...services.mapper_service import load_strategy_config

        strategy = load_strategy_config(strategy_name)
        if not strategy:
            raise HTTPException(
                status_code=404, detail=f"Strategy '{strategy_name}' not found"
            )

        # Get requirements
        required = await manager.get_resource_requirements(strategy)

        # Check current status
        resources = await manager.get_resource_status()
        status = {}
        for resource_name in required:
            resource = resources.get(resource_name)
            if resource:
                status[resource_name] = resource.status.value

        return {
            "strategy": strategy_name,
            "required_resources": required,
            "current_status": status,
            "ready": all(
                status.get(r) == ResourceStatus.HEALTHY.value for r in required
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting requirements: {str(e)}"
        )


@router.post("/ensure-required")
async def ensure_required_resources(
    manager: ResourceManager = Depends(get_resource_manager),
) -> Dict[str, Any]:
    """Ensure all required resources are available."""
    try:
        results = await manager.ensure_required_resources()

        return {
            "success": all(results.values()) if results else True,
            "resources": results,
            "message": "All required resources are available"
            if all(results.values())
            else "Some required resources failed to start",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error ensuring resources: {str(e)}"
        )


@router.get("/dashboard", response_class=HTMLResponse)
async def resource_dashboard():
    """Simple HTML dashboard for resource monitoring."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Biomapper Resource Monitor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 {
                color: #333;
            }
            .resource {
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .resource-info {
                flex: 1;
            }
            .resource-name {
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 5px;
            }
            .resource-type {
                color: #666;
                font-size: 14px;
            }
            .status {
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 12px;
            }
            .healthy { 
                background: #90EE90; 
                color: #2d5016;
            }
            .degraded { 
                background: #FFD700; 
                color: #664400;
            }
            .unavailable { 
                background: #FFB6C1; 
                color: #660000;
            }
            .starting, .stopping {
                background: #87CEEB;
                color: #003366;
            }
            .unknown {
                background: #D3D3D3;
                color: #333;
            }
            .error {
                color: #cc0000;
                font-size: 14px;
                margin-top: 5px;
            }
            .last-check {
                color: #999;
                font-size: 12px;
                margin-top: 5px;
            }
            .actions {
                margin-left: 20px;
            }
            button {
                padding: 5px 10px;
                margin: 0 2px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }
            .start-btn {
                background: #4CAF50;
                color: white;
            }
            .stop-btn {
                background: #f44336;
                color: white;
            }
            .check-btn {
                background: #2196F3;
                color: white;
            }
            button:hover {
                opacity: 0.8;
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .summary {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .summary-item {
                display: inline-block;
                margin-right: 20px;
            }
            .loading {
                text-align: center;
                padding: 20px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <h1>Biomapper Resource Monitor</h1>
        <div id="summary" class="summary"></div>
        <div id="resources"></div>
        <div id="loading" class="loading">Loading resources...</div>
        
        <script>
            let ws = null;
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/api/resources/ws`);
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    updateResourceDisplay(data.resources);
                    updateSummary(data.summary);
                    document.getElementById('loading').style.display = 'none';
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    // Fall back to polling
                    setTimeout(fetchStatus, 2000);
                };
                
                ws.onclose = () => {
                    // Reconnect after 5 seconds
                    setTimeout(connectWebSocket, 5000);
                };
            }
            
            function updateSummary(summary) {
                if (!summary) return;
                
                const summaryEl = document.getElementById('summary');
                summaryEl.innerHTML = `
                    <div class="summary-item"><strong>Total:</strong> ${summary.total}</div>
                    <div class="summary-item"><strong>Healthy:</strong> <span style="color: #2d5016">${summary.healthy}</span></div>
                    <div class="summary-item"><strong>Degraded:</strong> <span style="color: #664400">${summary.degraded}</span></div>
                    <div class="summary-item"><strong>Unavailable:</strong> <span style="color: #660000">${summary.unavailable}</span></div>
                    <div class="summary-item"><strong>Unknown:</strong> ${summary.unknown}</div>
                `;
            }
            
            function updateResourceDisplay(resources) {
                const container = document.getElementById('resources');
                container.innerHTML = resources.map(r => `
                    <div class="resource">
                        <div class="resource-info">
                            <div class="resource-name">${r.name}</div>
                            <div class="resource-type">Type: ${r.type}</div>
                            ${r.error_message ? `<div class="error">Error: ${r.error_message}</div>` : ''}
                            <div class="last-check">Last check: ${new Date(r.last_check).toLocaleString()}</div>
                        </div>
                        <span class="status ${r.status}">${r.status}</span>
                        <div class="actions">
                            <button class="start-btn" onclick="startResource('${r.name}')" 
                                    ${r.status === 'healthy' || r.status === 'starting' ? 'disabled' : ''}>
                                Start
                            </button>
                            <button class="stop-btn" onclick="stopResource('${r.name}')"
                                    ${r.status === 'unavailable' || r.status === 'stopping' ? 'disabled' : ''}>
                                Stop
                            </button>
                            <button class="check-btn" onclick="checkResource('${r.name}')">
                                Check
                            </button>
                        </div>
                    </div>
                `).join('');
            }
            
            async function startResource(name) {
                try {
                    const response = await fetch(`/api/resources/${name}/start`, { method: 'POST' });
                    const data = await response.json();
                    if (!data.success) {
                        alert(`Failed to start ${name}: ${data.message || 'Unknown error'}`);
                    }
                    fetchStatus();
                } catch (error) {
                    alert(`Error starting ${name}: ${error}`);
                }
            }
            
            async function stopResource(name) {
                try {
                    const response = await fetch(`/api/resources/${name}/stop`, { method: 'POST' });
                    const data = await response.json();
                    if (!data.success) {
                        alert(`Failed to stop ${name}: ${data.message || 'Unknown error'}`);
                    }
                    fetchStatus();
                } catch (error) {
                    alert(`Error stopping ${name}: ${error}`);
                }
            }
            
            async function checkResource(name) {
                try {
                    const response = await fetch(`/api/resources/${name}/check`, { method: 'POST' });
                    const data = await response.json();
                    fetchStatus();
                } catch (error) {
                    alert(`Error checking ${name}: ${error}`);
                }
            }
            
            async function fetchStatus() {
                try {
                    const response = await fetch('/api/resources/status');
                    const data = await response.json();
                    updateResourceDisplay(data.resources);
                    updateSummary(data.summary);
                    document.getElementById('loading').style.display = 'none';
                } catch (error) {
                    console.error('Error fetching status:', error);
                }
            }
            
            // Initial fetch
            fetchStatus();
            
            // Try to connect WebSocket for real-time updates
            connectWebSocket();
        </script>
    </body>
    </html>
    """


@router.websocket("/ws")
async def websocket_resources(
    websocket: WebSocket, manager: ResourceManager = Depends(get_resource_manager)
):
    """WebSocket endpoint for real-time resource status updates."""
    await websocket.accept()
    try:
        while True:
            # Get current resource status
            resources = await manager.get_resource_status()

            # Convert to list of dicts
            resource_list = []
            for resource in resources.values():
                resource_dict = resource.dict()
                resource_dict["last_check"] = resource_dict["last_check"].isoformat()
                resource_list.append(resource_dict)

            # Calculate summary
            summary = {
                "total": len(resources),
                "healthy": sum(
                    1 for r in resources.values() if r.status == ResourceStatus.HEALTHY
                ),
                "degraded": sum(
                    1 for r in resources.values() if r.status == ResourceStatus.DEGRADED
                ),
                "unavailable": sum(
                    1
                    for r in resources.values()
                    if r.status == ResourceStatus.UNAVAILABLE
                ),
                "unknown": sum(
                    1 for r in resources.values() if r.status == ResourceStatus.UNKNOWN
                ),
            }

            # Send update
            await websocket.send_json({"resources": resource_list, "summary": summary})

            # Wait before next update
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()
