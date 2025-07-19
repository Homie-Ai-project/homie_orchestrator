# API modules for orchestrator

from .router import router

__all__ = ['router']


class ServiceUpdateRequest(BaseModel):
    """Request model for service updates"""
    image: Optional[str] = None
    enabled: Optional[bool] = None
    restart_policy: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


class ContainerActionRequest(BaseModel):
    """Request model for container actions"""
    action: str  # start, stop, restart, remove
    timeout: Optional[int] = 30
    force: Optional[bool] = False


@router.get("/info", response_model=OrchestratorInfo)
async def get_orchestrator_info():
    """Get orchestrator information"""
    return OrchestratorInfo(
        name="Homei Orchestrator",
        version="1.0.0",
        status="running"
    )


@router.get("/containers", response_model=Dict[str, ContainerInfo])
async def list_containers(container_manager=Depends(get_container_manager)):
    """List all managed containers"""
    try:
        containers = await container_manager.list_containers()
        return containers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list containers: {str(e)}"
        )


@router.get("/containers/{service_name}", response_model=ContainerInfo)
async def get_container(service_name: str, container_manager=Depends(get_container_manager)):
    """Get information about a specific container"""
    try:
        containers = await container_manager.list_containers()
        if service_name not in containers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Container for service '{service_name}' not found"
            )
        return containers[service_name]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get container info: {str(e)}"
        )


@router.post("/containers/{service_name}/action")
async def container_action(
    service_name: str,
    request: ContainerActionRequest,
    container_manager=Depends(get_container_manager)
):
    """Perform action on a container"""
    try:
        success = False
        
        if request.action == "start":
            success = await container_manager.start_container(service_name)
        elif request.action == "stop":
            success = await container_manager.stop_container(service_name, request.timeout)
        elif request.action == "restart":
            success = await container_manager.restart_container(service_name, request.timeout)
        elif request.action == "remove":
            success = await container_manager.remove_container(service_name, request.force)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}"
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to {request.action} container"
            )
        
        return JSONResponse(
            content={"message": f"Successfully {request.action}ed container"},
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform action: {str(e)}"
        )


@router.get("/containers/{service_name}/logs", response_model=ContainerLogs)
async def get_container_logs(
    service_name: str,
    tail: int = 100,
    container_manager=Depends(get_container_manager)
):
    """Get container logs"""
    try:
        logs = await container_manager.get_container_logs(service_name, tail)
        return ContainerLogs(service_name=service_name, logs=logs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get logs: {str(e)}"
        )


@router.get("/containers/{service_name}/stats", response_model=ContainerStats)
async def get_container_stats(
    service_name: str,
    container_manager=Depends(get_container_manager)
):
    """Get container statistics"""
    try:
        stats = await container_manager.get_container_stats(service_name)
        if stats is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stats not available for service '{service_name}'"
            )
        return ContainerStats(service_name=service_name, stats=stats)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.get("/containers/{service_name}/status")
async def get_container_status(
    service_name: str,
    container_manager=Depends(get_container_manager)
):
    """Get container status"""
    try:
        status_value = await container_manager.get_container_status(service_name)
        return {"service_name": service_name, "status": status_value}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.post("/services/{service_name}/create")
async def create_service(
    service_name: str,
    config: ServiceConfigModel,
    container_manager=Depends(get_container_manager)
):
    """Create a new service"""
    try:
        # Convert Pydantic model to ServiceConfig
        from ..config import ServiceConfig
        service_config = ServiceConfig(**config.dict())
        
        # Pull image first
        await container_manager.pull_image(service_config.image)
        
        # Create container
        success = await container_manager.create_container(service_name, service_config)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create service"
            )
        
        return JSONResponse(
            content={"message": f"Successfully created service '{service_name}'"},
            status_code=status.HTTP_201_CREATED
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service: {str(e)}"
        )


@router.put("/services/{service_name}/update")
async def update_service(
    service_name: str,
    request: ServiceUpdateRequest,
    container_manager=Depends(get_container_manager)
):
    """Update an existing service"""
    try:
        # Get current config
        from ..config import get_service_config, ServiceConfig
        current_config = get_service_config(service_name)
        
        if not current_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found"
            )
        
        # Update config with provided values
        updated_data = current_config.dict()
        if request.image:
            updated_data["image"] = request.image
        if request.enabled is not None:
            updated_data["enabled"] = request.enabled
        if request.restart_policy:
            updated_data["restart_policy"] = request.restart_policy
        if request.environment:
            updated_data["environment"].update(request.environment)
        
        updated_config = ServiceConfig(**updated_data)
        
        # Update container
        success = await container_manager.update_container(service_name, updated_config)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service"
            )
        
        return JSONResponse(
            content={"message": f"Successfully updated service '{service_name}'"},
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update service: {str(e)}"
        )


@router.delete("/services/{service_name}")
async def delete_service(
    service_name: str,
    force: bool = False,
    container_manager=Depends(get_container_manager)
):
    """Delete a service and its container"""
    try:
        success = await container_manager.remove_container(service_name, force)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete service"
            )
        
        return JSONResponse(
            content={"message": f"Successfully deleted service '{service_name}'"},
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete service: {str(e)}"
        )


@router.get("/health")
async def health_check(health_monitor=Depends(get_health_monitor)):
    """Get orchestrator health status"""
    try:
        # Get health status from health monitor
        health_status = await health_monitor.get_overall_health()
        
        return {
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "checks": health_status["checks"],
            "timestamp": health_status["timestamp"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health status: {str(e)}"
        )
