"""
Proxy layer for communicating with the embedded Go service.

This module handles HTTP communication between the Python FastAPI service
and the embedded Go service, including JWT authentication and request forwarding.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

import httpx
from fastapi import HTTPException, UploadFile

from .internal_jwt import get_internal_jwt_token


logger = logging.getLogger(__name__)


class GoServiceProxy:
    """Proxy for communicating with the embedded Go service."""
    
    def __init__(self, base_url: str = "http://localhost:9091"):
        self.base_url = base_url
        self.timeout = httpx.Timeout(30.0)  # 30 second timeout
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        user_id: Optional[str] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        Make an authenticated request to the Go service.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/v1/evidence")
            user_id: User ID for context
            json_data: JSON payload
            files: Files for upload
            headers: Additional headers
            
        Returns:
            HTTP response
            
        Raises:
            HTTPException: If request fails
        """
        # Generate internal JWT token
        token = get_internal_jwt_token(user_id=user_id)
        
        # Prepare headers
        request_headers = {
            "X-Internal-Authorization": token,
            "X-User-ID": user_id or "system"
        }
        if headers:
            request_headers.update(headers)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    files=files,
                    headers=request_headers
                )
                return response
                
        except httpx.TimeoutException:
            logger.error(f"Timeout making {method} request to {url}")
            raise HTTPException(status_code=504, detail="Go service timeout")
        except httpx.RequestError as e:
            logger.error(f"Request error making {method} request to {url}: {e}")
            raise HTTPException(status_code=503, detail="Go service unavailable")
    
    async def submit_evidence(
        self,
        session_id: str,
        evidence_type: str,
        file: UploadFile,
        sha256_hash: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Submit evidence to the Go service.
        
        Args:
            session_id: Test session ID
            evidence_type: Type of evidence
            file: Uploaded file
            sha256_hash: File hash for verification
            user_id: User ID for context
            metadata: Additional metadata
            
        Returns:
            Response from Go service
        """
        # Prepare file upload
        file_content = await file.read()
        files = {
            "file": (file.filename, file_content, file.content_type)
        }
        
        # Prepare form data
        form_data = {
            "session_id": session_id,
            "evidence_type": evidence_type,
            "sha256_hash": sha256_hash,
            "filename": file.filename or "unknown"
        }
        
        if metadata:
            form_data["metadata"] = json.dumps(metadata)
        
        response = await self._make_request(
            method="POST",
            endpoint="/v1/evidence",
            user_id=user_id,
            files={**files, **{k: (None, v) for k, v in form_data.items()}}
        )
        
        if response.status_code != 200:
            logger.error(f"Evidence submission failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Evidence submission failed: {response.text}"
            )
        
        return response.json()
    
    async def submit_test_results(
        self,
        session_id: str,
        results: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit test results to the Go service for CRDT processing.
        
        Args:
            session_id: Test session ID
            results: Test results data
            user_id: User ID for context
            
        Returns:
            Response from Go service
        """
        payload = {
            "session_id": session_id,
            "results": results
        }
        
        response = await self._make_request(
            method="POST",
            endpoint=f"/v1/tests/sessions/{session_id}/results",
            user_id=user_id,
            json_data=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Test results submission failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Test results submission failed: {response.text}"
            )
        
        return response.json()
    
    async def classify_fault(
        self,
        rule_code: str,
        fault_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit fault classification to the Go service.
        
        Args:
            rule_code: AS1851 rule code
            fault_type: Type of fault
            description: Fault description
            metadata: Additional metadata
            user_id: User ID for context
            
        Returns:
            Classification response
        """
        payload = {
            "rule_code": rule_code,
            "fault_type": fault_type,
            "description": description,
            "metadata": metadata or {}
        }
        
        response = await self._make_request(
            method="POST",
            endpoint="/v1/classify",
            user_id=user_id,
            json_data=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Fault classification failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Fault classification failed: {response.text}"
            )
        
        return response.json()
    
    async def health_check(self) -> bool:
        """
        Check if the Go service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health"
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Go service health check failed: {e}")
            return False


# Global instance
go_service_proxy = GoServiceProxy()


async def get_go_service_proxy() -> GoServiceProxy:
    """Dependency to get the Go service proxy."""
    return go_service_proxy

def create_internal_token() -> str:
    """Create short-lived JWT for internal service communication"""
    from .internal_jwt import get_internal_jwt_token
    return get_internal_jwt_token()