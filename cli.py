#!/usr/bin/env python3
"""
Homie Orchestrator CLI

Command-line interface for managing the orchestrator.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestrator.config import get_settings
from orchestrator.core.container_manager import ContainerManager

app = typer.Typer(name="orchestrator", help="Homie Orchestrator CLI")
console = Console()


@app.command()
def status():
    """Show orchestrator status"""
    console.print("[bold green]Homie Orchestrator Status[/bold green]")
    
    # Show configuration
    settings = get_settings()
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Name", settings.orchestrator.name)
    table.add_row("Version", settings.orchestrator.version)
    table.add_row("API Host", settings.orchestrator.api.host)
    table.add_row("API Port", str(settings.orchestrator.api.port))
    table.add_row("Docker Socket", settings.orchestrator.docker.socket_path)
    table.add_row("Network", settings.orchestrator.docker.network_name)
    
    console.print(table)


@app.command()
def containers():
    """List managed containers"""
    asyncio.run(_list_containers())


async def _list_containers():
    """Async function to list containers"""
    try:
        settings = get_settings()
        manager = ContainerManager(
            docker_socket=settings.orchestrator.docker.socket_path,
            network_name=settings.orchestrator.docker.network_name
        )
        
        await manager.initialize()
        containers = await manager.list_containers()
        
        if not containers:
            console.print("[yellow]No containers found[/yellow]")
            return
        
        table = Table(title="Managed Containers")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Image", style="green")
        table.add_column("Created", style="blue")
        
        for service_name, info in containers.items():
            status_color = "green" if info.get("status") == "running" else "red"
            table.add_row(
                service_name,
                f"[{status_color}]{info.get('status', 'unknown')}[/{status_color}]",
                info.get("image", "unknown"),
                info.get("created", "unknown")
            )
        
        console.print(table)
        
        await manager.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def start_service(service_name: str):
    """Start a service"""
    asyncio.run(_start_service(service_name))


async def _start_service(service_name: str):
    """Async function to start a service"""
    try:
        settings = get_settings()
        manager = ContainerManager(
            docker_socket=settings.orchestrator.docker.socket_path,
            network_name=settings.orchestrator.docker.network_name
        )
        
        await manager.initialize()
        success = await manager.start_container(service_name)
        
        if success:
            console.print(f"[green]Successfully started service: {service_name}[/green]")
        else:
            console.print(f"[red]Failed to start service: {service_name}[/red]")
        
        await manager.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def stop_service(service_name: str):
    """Stop a service"""
    asyncio.run(_stop_service(service_name))


async def _stop_service(service_name: str):
    """Async function to stop a service"""
    try:
        settings = get_settings()
        manager = ContainerManager(
            docker_socket=settings.orchestrator.docker.socket_path,
            network_name=settings.orchestrator.docker.network_name
        )
        
        await manager.initialize()
        success = await manager.stop_container(service_name)
        
        if success:
            console.print(f"[green]Successfully stopped service: {service_name}[/green]")
        else:
            console.print(f"[red]Failed to stop service: {service_name}[/red]")
        
        await manager.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def logs(service_name: str, tail: int = 100):
    """Get service logs"""
    asyncio.run(_get_logs(service_name, tail))


async def _get_logs(service_name: str, tail: int):
    """Async function to get logs"""
    try:
        settings = get_settings()
        manager = ContainerManager(
            docker_socket=settings.orchestrator.docker.socket_path,
            network_name=settings.orchestrator.docker.network_name
        )
        
        await manager.initialize()
        logs = await manager.get_container_logs(service_name, tail)
        
        console.print(f"[bold]Logs for {service_name} (last {tail} lines):[/bold]")
        console.print(logs)
        
        await manager.cleanup()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@app.command()
def config(show: bool = typer.Option(False, "--show", help="Show current configuration")):
    """Manage orchestrator configuration"""
    if show:
        settings = get_settings()
        config_dict = settings.dict()
        console.print(yaml.dump(config_dict, default_flow_style=False))


if __name__ == "__main__":
    app()
