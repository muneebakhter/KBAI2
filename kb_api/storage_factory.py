#!/usr/bin/env python3
"""
Storage factory for KBAI - creates the appropriate storage backend based on configuration.
"""

import os
from typing import Optional
from kb_api.storage_interface import StorageInterface
from kb_api.storage import FileStorageManager


def create_storage_backend(
    storage_type: str = "file",
    base_dir: str = ".",
    azure_storage_connection_string: Optional[str] = None,
    azure_fileshare_name: str = "kbai-data",
    azure_blob_container_name: str = "kbai-data",
    cosmos_endpoint: Optional[str] = None,
    cosmos_key: Optional[str] = None,
    cosmos_database_name: str = "kbai-db"
) -> StorageInterface:
    """
    Create a storage backend based on the specified type.
    
    Args:
        storage_type: Type of storage backend ("file", "azure_fileshare", "azure_blob", "cosmosdb")
        base_dir: Base directory for file storage (only used for "file" type)
        azure_storage_connection_string: Azure Storage connection string (for fileshare and blob)
        azure_fileshare_name: Azure File Share name
        azure_blob_container_name: Azure Blob Container name
        cosmos_endpoint: CosmosDB endpoint URL
        cosmos_key: CosmosDB primary key
        cosmos_database_name: CosmosDB database name
    
    Returns:
        StorageInterface: Configured storage backend
    
    Raises:
        ValueError: If invalid storage type or missing required configuration
        ImportError: If required Azure SDK packages are not installed
    """
    
    storage_type = storage_type.lower()
    
    if storage_type == "file":
        return FileStorageManager(base_dir)
    
    elif storage_type == "azure_fileshare":
        if not azure_storage_connection_string:
            raise ValueError("azure_storage_connection_string is required for Azure File Share storage")
        
        try:
            from kb_api.azure_fileshare_storage import AzureFileShareStorage
            return AzureFileShareStorage(azure_storage_connection_string, azure_fileshare_name)
        except ImportError as e:
            raise ImportError(f"Azure File Share storage requires azure-storage-file-share package: {e}")
    
    elif storage_type == "azure_blob":
        if not azure_storage_connection_string:
            raise ValueError("azure_storage_connection_string is required for Azure Blob storage")
        
        try:
            from kb_api.azure_blob_storage import AzureBlobStorage
            return AzureBlobStorage(azure_storage_connection_string, azure_blob_container_name)
        except ImportError as e:
            raise ImportError(f"Azure Blob storage requires azure-storage-blob package: {e}")
    
    elif storage_type == "cosmosdb":
        if not cosmos_endpoint or not cosmos_key:
            raise ValueError("cosmos_endpoint and cosmos_key are required for CosmosDB storage")
        
        try:
            from kb_api.azure_cosmosdb_storage import AzureCosmosDBStorage
            return AzureCosmosDBStorage(cosmos_endpoint, cosmos_key, cosmos_database_name)
        except ImportError as e:
            raise ImportError(f"CosmosDB storage requires azure-cosmos package: {e}")
    
    else:
        raise ValueError(f"Unknown storage type: {storage_type}. Supported types: file, azure_fileshare, azure_blob, cosmosdb")


def create_storage_from_env(base_dir: str = ".") -> StorageInterface:
    """
    Create storage backend based on environment variables.
    
    Environment variables:
        STORAGE_TYPE: Type of storage ("file", "azure_fileshare", "azure_blob", "cosmosdb")
        AZURE_STORAGE_CONNECTION_STRING: Azure Storage connection string
        AZURE_FILESHARE_NAME: Azure File Share name (default: "kbai-data")
        AZURE_BLOB_CONTAINER_NAME: Azure Blob Container name (default: "kbai-data")
        COSMOS_ENDPOINT: CosmosDB endpoint URL
        COSMOS_KEY: CosmosDB primary key
        COSMOS_DATABASE_NAME: CosmosDB database name (default: "kbai-db")
    
    Args:
        base_dir: Base directory for file storage (fallback)
    
    Returns:
        StorageInterface: Configured storage backend
    """
    
    storage_type = os.getenv("STORAGE_TYPE", "file")
    
    return create_storage_backend(
        storage_type=storage_type,
        base_dir=base_dir,
        azure_storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        azure_fileshare_name=os.getenv("AZURE_FILESHARE_NAME", "kbai-data"),
        azure_blob_container_name=os.getenv("AZURE_BLOB_CONTAINER_NAME", "kbai-data"),
        cosmos_endpoint=os.getenv("COSMOS_ENDPOINT"),
        cosmos_key=os.getenv("COSMOS_KEY"),
        cosmos_database_name=os.getenv("COSMOS_DATABASE_NAME", "kbai-db")
    )