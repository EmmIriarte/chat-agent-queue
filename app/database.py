"""Supabase database connection and queries"""
import logging
from typing import Optional, Dict, Any, List
from app.config import settings

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None
    create_client = None

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase client wrapper"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False
    
    def _initialize_client(self):
        """Initialize Supabase client (lazy initialization)"""
        if self._initialized:
            return
            
        try:
            if not SUPABASE_AVAILABLE:
                logger.warning("Supabase library not available")
                self._initialized = True
                return
                
            # Debug environment variables
            import os
            logger.info(f"Environment variables debug:")
            logger.info(f"  SUPABASE_URL (env): {os.getenv('SUPABASE_URL')}")
            logger.info(f"  SUPABASE_KEY (env): {os.getenv('SUPABASE_KEY')}")
            logger.info(f"  SUPABASE_SERVICE_ROLE_KEY (env): {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}")
            logger.info(f"  SUPABASE_URL (settings): {settings.SUPABASE_URL}")
            logger.info(f"  SUPABASE_KEY (settings): {settings.SUPABASE_KEY}")
            logger.info(f"  SUPABASE_SERVICE_ROLE_KEY (settings): {settings.SUPABASE_SERVICE_ROLE_KEY}")
                
            if not settings.SUPABASE_URL:
                logger.warning("Supabase URL not configured")
                self._initialized = True
                return
            
            # Use service role key if available (bypasses RLS), otherwise use anon key
            api_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
            
            if not api_key:
                logger.warning("Supabase API key not configured")
                self._initialized = True
                return
            
            self._client = create_client(settings.SUPABASE_URL, api_key)
            logger.info(f"Supabase client initialized successfully (using {'service_role' if settings.SUPABASE_SERVICE_ROLE_KEY else 'anon'} key)")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self._client = None
            self._initialized = True
    
    @property
    def client(self) -> Optional[Client]:
        """Lazy initialization of client"""
        if not self._initialized:
            self._initialize_client()
        return self._client
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the Supabase connection"""
        try:
            if not SUPABASE_AVAILABLE:
                return {
                    "status": "error",
                    "message": "Supabase library not available",
                    "connected": False
                }
                
            if not self.client:
                return {
                    "status": "error",
                    "message": "Supabase client not initialized",
                    "connected": False
                }
            
            # Try a simple query to test connection
            result = self.client.table("unipile_accounts").select("*").limit(1).execute()
            
            return {
                "status": "success",
                "message": "Supabase connection successful",
                "connected": True,
                "sample_records": len(result.data)
            }
            
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "connected": False
            }
    
    def get_account_mapping(self, unipile_account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get account info including LinkedIn provider_id and name
        
        Args:
            unipile_account_id: The Unipile account ID
            
        Returns:
            Dict with account_id, provider_id, and name, or None if not found
        """
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
            
            result = self.client.table("unipile_accounts")\
                .select("account_id, provider_id, name")\
                .eq("account_id", unipile_account_id)\
                .not_.is_("provider_id", "null")\
                .execute()
            
            if result.data and len(result.data) > 0:
                account = result.data[0]
                logger.info(f"Found account mapping: {unipile_account_id} -> {account['provider_id']}")
                return {
                    "unipile_account_id": account["account_id"],
                    "linkedin_provider_id": account["provider_id"],
                    "name": account.get("name", "the recruiter")
                }
            else:
                logger.warning(f"No account mapping found for: {unipile_account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying account mapping: {e}")
            return None
    
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all accounts from unipile_accounts table
        
        Returns:
            List of account dictionaries with account_id, provider_id, and name
        """
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return []
            
            result = self.client.table("unipile_accounts")\
                .select("account_id, provider_id, name")\
                .not_.is_("provider_id", "null")\
                .execute()
            
            if result.data:
                logger.info(f"Found {len(result.data)} accounts")
                return result.data
            else:
                logger.warning("No accounts found")
                return []
                
        except Exception as e:
            logger.error(f"Error querying all accounts: {e}")
            return []
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job information by job_id
        
        Args:
            job_id: The job identifier
            
        Returns:
            Dict with job info, or None if not found
        """
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
            
            # Query jobs table for specific fields
            result = self.client.table("jobs")\
                .select("id, title, description, client")\
                .eq("id", job_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                job = result.data[0]
                logger.info(f"Found job info for: {job_id} - {job.get('title')} (Client: {job.get('client')})")
                return {
                    "job_id": job.get("id"),
                    "job_title": job.get("title", "this position"),
                    "job_description": job.get("description", "a great opportunity"),
                    "client": job.get("client", "our client")
                }
            else:
                logger.warning(f"No job info found for: {job_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying job info: {e}")
            return None

# Global Supabase client instance - will be initialized after settings load
_supabase_client_singleton = None

def get_supabase_client():
    """Get or create the Supabase client instance"""
    global _supabase_client_singleton
    if _supabase_client_singleton is None:
        _supabase_client_singleton = SupabaseClient()
    return _supabase_client_singleton

# For backwards compatibility
supabase_client = get_supabase_client
