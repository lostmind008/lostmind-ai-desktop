"""
Google Cloud Storage Service for LostMindAI Backend.
Handles file upload, download, and management in Google Cloud Storage.
"""

import os
import logging
from typing import Optional, List, BinaryIO
from pathlib import Path
import asyncio

from google.cloud import storage
from google.api_core import exceptions as gcp_exceptions

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GCSService:
    """Google Cloud Storage service for file management"""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """Initialize GCS service with bucket configuration"""
        self.bucket_name = bucket_name or getattr(settings, 'GCS_BUCKET_NAME', 'lostmindai-storage')
        self._client = None
        self._bucket = None
        
    def _get_client(self) -> storage.Client:
        """Get GCS client instance (lazy initialization)"""
        if self._client is None:
            try:
                self._client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
            except Exception as e:
                logger.warning(f"Failed to initialize GCS client: {e}")
                # For testing, create a mock client
                self._client = None
        return self._client
    
    def _get_bucket(self) -> Optional[storage.Bucket]:
        """Get GCS bucket instance"""
        if self._bucket is None:
            client = self._get_client()
            if client:
                try:
                    self._bucket = client.bucket(self.bucket_name)
                except Exception as e:
                    logger.warning(f"Failed to get GCS bucket {self.bucket_name}: {e}")
                    return None
        return self._bucket
    
    async def upload_to_gcs(
        self, 
        file_content: bytes, 
        destination_path: str,
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload file content to GCS and return the GCS URI.
        
        Args:
            file_content: File content as bytes
            destination_path: Path in the bucket where file should be stored
            content_type: MIME type of the file
            
        Returns:
            GCS URI of uploaded file, or None if upload failed
        """
        try:
            # Run the blocking GCS operation in a thread pool
            return await asyncio.get_event_loop().run_in_executor(
                None, self._upload_sync, file_content, destination_path, content_type
            )
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            return None
    
    def _upload_sync(
        self, 
        file_content: bytes, 
        destination_path: str, 
        content_type: Optional[str] = None
    ) -> Optional[str]:
        """Synchronous upload to GCS"""
        bucket = self._get_bucket()
        if not bucket:
            logger.warning("GCS bucket not available, skipping upload")
            return None
            
        try:
            blob = bucket.blob(destination_path)
            
            if content_type:
                blob.content_type = content_type
                
            blob.upload_from_string(file_content)
            
            # Return GCS URI
            gcs_uri = f"gs://{self.bucket_name}/{destination_path}"
            logger.info(f"Successfully uploaded file to {gcs_uri}")
            return gcs_uri
            
        except gcp_exceptions.GoogleCloudError as e:
            logger.error(f"GCS upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during GCS upload: {e}")
            return None
    
    async def download_from_gcs(self, gcs_path: str) -> Optional[bytes]:
        """
        Download file content from GCS.
        
        Args:
            gcs_path: Path in the bucket or full GCS URI
            
        Returns:
            File content as bytes, or None if download failed
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._download_sync, gcs_path
            )
        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            return None
    
    def _download_sync(self, gcs_path: str) -> Optional[bytes]:
        """Synchronous download from GCS"""
        bucket = self._get_bucket()
        if not bucket:
            logger.warning("GCS bucket not available, skipping download")
            return None
            
        try:
            # Handle both gs:// URIs and plain paths
            if gcs_path.startswith("gs://"):
                # Extract path from URI
                path_parts = gcs_path.replace("gs://", "").split("/", 1)
                if len(path_parts) == 2:
                    blob_path = path_parts[1]
                else:
                    blob_path = gcs_path
            else:
                blob_path = gcs_path
                
            blob = bucket.blob(blob_path)
            content = blob.download_as_bytes()
            
            logger.info(f"Successfully downloaded file from {gcs_path}")
            return content
            
        except gcp_exceptions.NotFound:
            logger.warning(f"File not found in GCS: {gcs_path}")
            return None
        except gcp_exceptions.GoogleCloudError as e:
            logger.error(f"GCS download error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during GCS download: {e}")
            return None
    
    async def delete_file(self, gcs_path: str) -> bool:
        """
        Delete a file from GCS.
        
        Args:
            gcs_path: Path in the bucket or full GCS URI
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._delete_file_sync, gcs_path
            )
        except Exception as e:
            logger.error(f"Failed to delete from GCS: {e}")
            return False
    
    def _delete_file_sync(self, gcs_path: str) -> bool:
        """Synchronous file deletion from GCS"""
        bucket = self._get_bucket()
        if not bucket:
            logger.warning("GCS bucket not available, skipping deletion")
            return False
            
        try:
            # Handle both gs:// URIs and plain paths
            if gcs_path.startswith("gs://"):
                path_parts = gcs_path.replace("gs://", "").split("/", 1)
                if len(path_parts) == 2:
                    blob_path = path_parts[1]
                else:
                    blob_path = gcs_path
            else:
                blob_path = gcs_path
                
            blob = bucket.blob(blob_path)
            blob.delete()
            
            logger.info(f"Successfully deleted file from {gcs_path}")
            return True
            
        except gcp_exceptions.NotFound:
            logger.warning(f"File not found for deletion: {gcs_path}")
            return True  # Consider missing file as successful deletion
        except gcp_exceptions.GoogleCloudError as e:
            logger.error(f"GCS deletion error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during GCS deletion: {e}")
            return False
    
    async def delete_prefix(self, prefix: str) -> bool:
        """
        Delete all files with a given prefix from GCS.
        
        Args:
            prefix: Prefix to match for deletion
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._delete_prefix_sync, prefix
            )
        except Exception as e:
            logger.error(f"Failed to delete prefix from GCS: {e}")
            return False
    
    def _delete_prefix_sync(self, prefix: str) -> bool:
        """Synchronous prefix deletion from GCS"""
        bucket = self._get_bucket()
        if not bucket:
            logger.warning("GCS bucket not available, skipping prefix deletion")
            return False
            
        try:
            # List all blobs with the prefix
            blobs = bucket.list_blobs(prefix=prefix)
            
            deleted_count = 0
            for blob in blobs:
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete blob {blob.name}: {e}")
                    
            logger.info(f"Successfully deleted {deleted_count} files with prefix {prefix}")
            return True
            
        except gcp_exceptions.GoogleCloudError as e:
            logger.error(f"GCS prefix deletion error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during GCS prefix deletion: {e}")
            return False
    
    async def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """
        List files in the GCS bucket.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file paths in the bucket
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._list_files_sync, prefix
            )
        except Exception as e:
            logger.error(f"Failed to list files from GCS: {e}")
            return []
    
    def _list_files_sync(self, prefix: Optional[str] = None) -> List[str]:
        """Synchronous file listing from GCS"""
        bucket = self._get_bucket()
        if not bucket:
            logger.warning("GCS bucket not available, returning empty list")
            return []
            
        try:
            blobs = bucket.list_blobs(prefix=prefix) if prefix else bucket.list_blobs()
            file_paths = [blob.name for blob in blobs]
            
            logger.info(f"Listed {len(file_paths)} files from GCS bucket")
            return file_paths
            
        except gcp_exceptions.GoogleCloudError as e:
            logger.error(f"GCS list error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during GCS listing: {e}")
            return []