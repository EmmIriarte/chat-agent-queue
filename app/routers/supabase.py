"""Supabase database query routes"""
import logging
from fastapi import APIRouter, HTTPException
from app.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/supabase", tags=["supabase"])


@router.get("/test")
async def test_supabase():
    """Test Supabase connection"""
    return get_supabase_client().test_connection()


@router.get("/account/{unipile_account_id}")
async def get_account_mapping(unipile_account_id: str):
    """Get LinkedIn provider_id for a Unipile account_id"""
    mapping = get_supabase_client().get_account_mapping(unipile_account_id)
    if mapping:
        return mapping
    else:
        raise HTTPException(status_code=404, detail=f"Account mapping not found for: {unipile_account_id}")


@router.get("/job/{job_id}")
async def get_job_info(job_id: str):
    """Get job information by job_id"""
    job_info = get_supabase_client().get_job_info(job_id)
    if job_info:
        return job_info
    else:
        raise HTTPException(status_code=404, detail=f"Job info not found for: {job_id}")


@router.get("/accounts/list")
async def list_all_accounts():
    """List all accounts in the unipile_accounts table"""
    try:
        if not get_supabase_client().client:
            raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
        result = get_supabase_client().client.table("unipile_accounts").select("*").execute()
        
        return {
            "status": "success",
            "count": len(result.data),
            "accounts": result.data
        }
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing accounts: {str(e)}")
