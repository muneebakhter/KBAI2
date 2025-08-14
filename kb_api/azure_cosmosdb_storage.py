#!/usr/bin/env python3
"""
Azure CosmosDB storage backend for KBAI.
"""

import json
import uuid
from typing import List, Dict, Optional, Tuple
from kb_api.models import FAQEntry, KBEntry
from kb_api.storage_interface import StorageInterface

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions
    HAS_COSMOS = True
except ImportError:
    HAS_COSMOS = False


class AzureCosmosDBStorage(StorageInterface):
    """Azure CosmosDB storage backend"""
    
    def __init__(self, endpoint: str, key: str, database_name: str = "kbai-db"):
        if not HAS_COSMOS:
            raise ImportError("azure-cosmos package is required for Azure CosmosDB storage")
        
        self.endpoint = endpoint
        self.key = key
        self.database_name = database_name
        
        # Initialize CosmosDB client
        self.client = CosmosClient(endpoint, key)
        
        # Ensure database exists
        try:
            self.database = self.client.create_database(database_name)
        except exceptions.CosmosResourceExistsError:
            self.database = self.client.get_database_client(database_name)
        
        # Ensure containers exist
        self._ensure_containers()
    
    def _ensure_containers(self):
        """Ensure all required containers exist"""
        containers = [
            ("projects", "/project_id"),
            ("faqs", "/project_id"),
            ("kb_entries", "/project_id"),
            ("attachments_metadata", "/project_id"),
            ("index_metadata", "/project_id")
        ]
        
        for container_name, partition_key in containers:
            try:
                self.database.create_container(
                    id=container_name,
                    partition_key=PartitionKey(path=partition_key)
                )
            except exceptions.CosmosResourceExistsError:
                pass  # Container already exists
    
    def _get_container(self, container_name: str):
        """Get container client"""
        return self.database.get_container_client(container_name)
    
    def create_or_update_project(self, project_id: str, project_name: str) -> bool:
        """Create or update a project. Returns True if new, False if updated."""
        container = self._get_container("projects")
        
        try:
            # Try to get existing project
            item = container.read_item(item=project_id, partition_key=project_id)
            # Project exists, update it
            item["name"] = project_name
            item["active"] = True
            container.upsert_item(item)
            return False
        except exceptions.CosmosResourceNotFoundError:
            # Project doesn't exist, create it
            item = {
                "id": project_id,
                "project_id": project_id,
                "name": project_name,
                "active": True
            }
            container.create_item(item)
            return True
    
    def load_project_mapping(self) -> Dict[str, str]:
        """Load project mapping from CosmosDB"""
        container = self._get_container("projects")
        
        query = "SELECT p.id, p.name FROM projects p WHERE p.active = true"
        projects = {}
        
        for item in container.query_items(query=query, enable_cross_partition_query=True):
            projects[item["id"]] = item["name"]
        
        return projects
    
    def load_faqs(self, project_id: str) -> List[FAQEntry]:
        """Load FAQ entries for a project"""
        container = self._get_container("faqs")
        
        query = "SELECT * FROM faqs f WHERE f.project_id = @project_id"
        parameters = [{"name": "@project_id", "value": project_id}]
        
        faqs = []
        for item in container.query_items(query=query, parameters=parameters):
            # Remove CosmosDB specific fields
            faq_data = {k: v for k, v in item.items() if k not in ["_rid", "_self", "_etag", "_attachments", "_ts"]}
            faqs.append(FAQEntry.from_dict(faq_data))
        
        return faqs
    
    def load_kb_entries(self, project_id: str) -> List[KBEntry]:
        """Load KB entries for a project"""
        container = self._get_container("kb_entries")
        
        query = "SELECT * FROM kb_entries k WHERE k.project_id = @project_id"
        parameters = [{"name": "@project_id", "value": project_id}]
        
        entries = []
        for item in container.query_items(query=query, parameters=parameters):
            # Remove CosmosDB specific fields
            entry_data = {k: v for k, v in item.items() if k not in ["_rid", "_self", "_etag", "_attachments", "_ts"]}
            entries.append(KBEntry.from_dict(entry_data))
        
        return entries
    
    def save_faqs(self, project_id: str, faqs: List[FAQEntry]):
        """Save FAQ entries to CosmosDB"""
        container = self._get_container("faqs")
        
        for faq in faqs:
            item = faq.to_dict()
            item["project_id"] = project_id
            container.upsert_item(item)
    
    def save_kb_entries(self, project_id: str, kb_entries: List[KBEntry]):
        """Save KB entries to CosmosDB"""
        container = self._get_container("kb_entries")
        
        for entry in kb_entries:
            item = entry.to_dict()
            item["project_id"] = project_id
            container.upsert_item(item)
    
    def upsert_faqs(self, project_id: str, new_faqs: List[FAQEntry], replace: bool = False) -> Tuple[List[str], List[str]]:
        """Upsert FAQ entries. Returns (created_ids, updated_ids)"""
        container = self._get_container("faqs")
        
        if replace:
            # Delete all existing FAQs for this project
            query = "SELECT f.id FROM faqs f WHERE f.project_id = @project_id"
            parameters = [{"name": "@project_id", "value": project_id}]
            
            for item in container.query_items(query=query, parameters=parameters):
                container.delete_item(item=item["id"], partition_key=project_id)
        
        # Get existing FAQs
        existing_faqs = self.load_faqs(project_id)
        existing_ids = {faq.id for faq in existing_faqs}
        
        created_ids = []
        updated_ids = []
        
        for faq in new_faqs:
            if faq.id in existing_ids:
                updated_ids.append(faq.id)
            else:
                created_ids.append(faq.id)
            
            item = faq.to_dict()
            item["project_id"] = project_id
            container.upsert_item(item)
        
        return created_ids, updated_ids
    
    def upsert_kb_entries(self, project_id: str, new_entries: List[KBEntry], replace: bool = False) -> Tuple[List[str], List[str]]:
        """Upsert KB entries. Returns (created_ids, updated_ids)"""
        container = self._get_container("kb_entries")
        
        if replace:
            # Delete all existing KB entries for this project
            query = "SELECT k.id FROM kb_entries k WHERE k.project_id = @project_id"
            parameters = [{"name": "@project_id", "value": project_id}]
            
            for item in container.query_items(query=query, parameters=parameters):
                container.delete_item(item=item["id"], partition_key=project_id)
        
        # Get existing entries
        existing_entries = self.load_kb_entries(project_id)
        existing_ids = {entry.id for entry in existing_entries}
        
        created_ids = []
        updated_ids = []
        
        for entry in new_entries:
            if entry.id in existing_ids:
                updated_ids.append(entry.id)
            else:
                created_ids.append(entry.id)
            
            item = entry.to_dict()
            item["project_id"] = project_id
            container.upsert_item(item)
        
        return created_ids, updated_ids
    
    def save_attachment(self, project_id: str, filename: str, content: bytes) -> str:
        """Save attachment metadata to CosmosDB. Note: Actual file should be stored in blob storage."""
        container = self._get_container("attachments_metadata")
        
        # Store metadata only - actual content should go to blob storage
        attachment_id = f"{project_id}_{filename}"
        item = {
            "id": attachment_id,
            "project_id": project_id,
            "filename": filename,
            "size": len(content),
            "content_type": self._get_content_type(filename)
        }
        
        container.upsert_item(item)
        
        # In a real implementation, this would upload to blob storage
        # For now, we'll store as base64 in metadata (not recommended for large files)
        import base64
        item["content_base64"] = base64.b64encode(content).decode('utf-8')
        container.upsert_item(item)
        
        return f"cosmosdb://{attachment_id}"
    
    def get_attachment(self, project_id: str, filename: str) -> Optional[bytes]:
        """Get attachment file content"""
        container = self._get_container("attachments_metadata")
        attachment_id = f"{project_id}_{filename}"
        
        try:
            item = container.read_item(item=attachment_id, partition_key=project_id)
            # In a real implementation, this would download from blob storage
            if "content_base64" in item:
                import base64
                return base64.b64decode(item["content_base64"])
            return None
        except exceptions.CosmosResourceNotFoundError:
            return None
    
    def delete_attachment(self, project_id: str, filename: str) -> bool:
        """Delete attachment file. Returns True if deleted, False if not found."""
        container = self._get_container("attachments_metadata")
        attachment_id = f"{project_id}_{filename}"
        
        try:
            container.delete_item(item=attachment_id, partition_key=project_id)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
    
    def list_attachments(self, project_id: str) -> List[str]:
        """List all attachment filenames for a project"""
        container = self._get_container("attachments_metadata")
        
        query = "SELECT a.filename FROM attachments_metadata a WHERE a.project_id = @project_id"
        parameters = [{"name": "@project_id", "value": project_id}]
        
        filenames = []
        for item in container.query_items(query=query, parameters=parameters):
            filenames.append(item["filename"])
        
        return filenames
    
    def delete_faq(self, project_id: str, faq_id: str) -> bool:
        """Delete a FAQ entry by ID. Returns True if deleted, False if not found."""
        container = self._get_container("faqs")
        
        try:
            # Get the FAQ to check for source files
            faq_item = container.read_item(item=faq_id, partition_key=project_id)
            faq = FAQEntry.from_dict(faq_item)
            
            # Delete the FAQ
            container.delete_item(item=faq_id, partition_key=project_id)
            
            # Clean up associated source file if it exists
            if faq.source_file:
                self.delete_attachment(project_id, faq.source_file)
            
            # Also try to clean up potential FAQ attachment files (multiple formats)
            potential_files = [
                f"{faq_id}-faq.txt",
                f"{faq_id}-faq.docx",
                f"{faq_id}-faq.pdf"
            ]
            for filename in potential_files:
                self.delete_attachment(project_id, filename)
            
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
    
    def delete_kb_entry(self, project_id: str, kb_id: str) -> bool:
        """Delete a KB entry by ID. Returns True if deleted, False if not found."""
        container = self._get_container("kb_entries")
        
        try:
            # Get the KB entry to check for source files
            kb_item = container.read_item(item=kb_id, partition_key=project_id)
            kb_entry = KBEntry.from_dict(kb_item)
            
            # Delete the KB entry
            container.delete_item(item=kb_id, partition_key=project_id)
            
            # Clean up associated source file if it exists
            if kb_entry.source_file:
                self.delete_attachment(project_id, kb_entry.source_file)
            
            # Also try to clean up potential KB attachment files (multiple formats)
            potential_files = [
                f"{kb_id}-kb.txt",
                f"{kb_id}-kb.docx", 
                f"{kb_id}-kb.pdf"
            ]
            for filename in potential_files:
                self.delete_attachment(project_id, filename)
            
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
    
    def get_faq_by_id(self, project_id: str, faq_id: str) -> Optional[FAQEntry]:
        """Get a specific FAQ by ID"""
        container = self._get_container("faqs")
        
        try:
            item = container.read_item(item=faq_id, partition_key=project_id)
            faq_data = {k: v for k, v in item.items() if k not in ["_rid", "_self", "_etag", "_attachments", "_ts"]}
            return FAQEntry.from_dict(faq_data)
        except exceptions.CosmosResourceNotFoundError:
            return None
    
    def get_kb_entry_by_id(self, project_id: str, kb_id: str) -> Optional[KBEntry]:
        """Get a specific KB entry by ID"""
        container = self._get_container("kb_entries")
        
        try:
            item = container.read_item(item=kb_id, partition_key=project_id)
            entry_data = {k: v for k, v in item.items() if k not in ["_rid", "_self", "_etag", "_attachments", "_ts"]}
            return KBEntry.from_dict(entry_data)
        except exceptions.CosmosResourceNotFoundError:
            return None
    
    def get_index_metadata(self, project_id: str) -> Dict:
        """Get index metadata for a project"""
        container = self._get_container("index_metadata")
        
        try:
            item = container.read_item(item=project_id, partition_key=project_id)
            return item.get("metadata", {"error": "No index metadata found"})
        except exceptions.CosmosResourceNotFoundError:
            return {"error": "No index metadata found"}
    
    def save_index_metadata(self, project_id: str, metadata: Dict):
        """Save index metadata for a project"""
        container = self._get_container("index_metadata")
        
        item = {
            "id": project_id,
            "project_id": project_id,
            "metadata": metadata
        }
        
        container.upsert_item(item)
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename"""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"