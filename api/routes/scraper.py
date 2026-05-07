"""
Scraper endpoints - Trigger and monitor job scraping
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import List
import subprocess
import asyncio
import os
from api import models, database

router = APIRouter()

# Track scraper process
scraper_process = None
is_scraper_running = False

@router.get("/status", response_model=models.ScraperStatus)
async def get_scraper_status():
    """Get current scraper status and statistics"""
    global is_scraper_running
    
    try:
        stats = await database.get_scraper_stats()
        
        return {
            "is_running": is_scraper_running,
            "last_run": None,  # Can be tracked in database if needed
            "jobs_scraped_total": stats.get("jobs_scraped_total", 0),
            "jobs_with_details": stats.get("jobs_with_details", 0),
            "pending_jobs": stats.get("pending_jobs", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting scraper status: {str(e)}")


@router.post("/trigger")
async def trigger_scraper(
    request: models.ScrapeTrigger,
    background_tasks: BackgroundTasks
):
    """
    Trigger the job scraper to run
    """
    global is_scraper_running
    
    if is_scraper_running:
        return {"message": "Scraper is already running", "status": "in_progress"}
    
    try:
        # Log the event
        await database.log_scrape_event("scraper_triggered", {
            "search_terms": request.search_terms,
            "full_details": request.full_details
        })
        
        # Add scraping task to background
        background_tasks.add_task(run_scraper, request.full_details)
        
        is_scraper_running = True
        
        return {
            "message": "Scraper started successfully",
            "status": "started",
            "full_details": request.full_details
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering scraper: {str(e)}")


async def run_scraper(fetch_details: bool = False):
    """
    Run the actual scraping in background
    """
    global is_scraper_running, scraper_process
    
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        log_path = os.path.join(project_root, "scraper.log")
        
        with open(log_path, "w") as log_file:
            # Run search_retriever.py
            scraper_process = await asyncio.create_subprocess_exec(
                "python", "-u", "search_retriever.py",
                cwd=project_root,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
            
            await asyncio.wait_for(scraper_process.wait(), timeout=3600)  # 1 hour timeout
            
            await database.log_scrape_event("search_retriever_completed", {
                "returncode": scraper_process.returncode
            })
            
            # Optionally run details_retriever.py
            if fetch_details:
                scraper_process = await asyncio.create_subprocess_exec(
                    "python", "-u", "details_retriever.py",
                    cwd=project_root,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
                
                await asyncio.wait_for(scraper_process.wait(), timeout=7200)  # 2 hours timeout
                
                await database.log_scrape_event("details_retriever_completed", {
                    "returncode": scraper_process.returncode
                })
        
        await database.log_scrape_event("scraper_completed", {
            "success": True,
            "fetch_details": fetch_details
        })
    
    except asyncio.TimeoutError:
        await database.log_scrape_event("scraper_timeout", {})
    
    except subprocess.TimeoutExpired:
        await database.log_scrape_event("scraper_timeout", {})
    
    except Exception as e:
        await database.log_scrape_event("scraper_error", {
            "error": str(e)
        })
    
    finally:
        is_scraper_running = False


@router.post("/stop")
async def stop_scraper():
    """Stop the running scraper"""
    global is_scraper_running, scraper_process
    
    if not is_scraper_running:
        return {"message": "No scraper is currently running"}
    
    try:
        # Kill process
        if scraper_process:
            scraper_process.terminate()
        
        is_scraper_running = False
        
        await database.log_scrape_event("scraper_stopped", {})
        
        return {"message": "Scraper stopped successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping scraper: {str(e)}")


@router.get("/logs")
async def get_scraper_logs(
    limit: int = Query(50),
    event_type: str = Query(None)
):
    """Get recent scraper logs from DB"""
    try:
        collection = database.database["scraper_logs"]
        filter_dict = {}
        
        if event_type:
            filter_dict["event_type"] = event_type
        
        cursor = collection.find(filter_dict).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        return {
            "logs": logs,
            "count": len(logs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")


@router.get("/live-logs")
async def get_live_logs():
    """Get raw text logs from the currently running scraper"""
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        log_path = os.path.join(project_root, "scraper.log")
        
        if not os.path.exists(log_path):
            return {"logs": "No active logs found (scraper has not run yet)."}
        
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Return last 200 lines to avoid massive payloads
            return {"logs": "".join(lines[-200:])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading live logs: {str(e)}")
