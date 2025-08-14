#!/usr/bin/env python3
"""
Azure Blob Storage backend for KBAI.
"""

import json
import mimetypes
from typing import List, Dict, Optional, Tuple
from kb_api.models import FAQEntry, KBEntry
from kb_api.storage_interface import StorageInterface

try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    HAS_AZURE_BLOB = True
except ImportError:
    HAS_AZURE_BLOB = False


class AzureBlobStorage(StorageInterface):
    """Azure Blob Storage backend"""
    
    def __init__(self, connection_string: str, container_name: str = "kbai-data"):
        if not HAS_AZURE_BLOB:
            raise ImportError("azure-storage-blob package is required for Azure Blob Storage")
        
        self.connection_string = connection_string
        self.container_name = container_name
        
        # Initialize Azure Blob client
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Ensure container exists
        try:
            self.blob_service_client.create_container(container_name)
        except Exception:
            pass  # Container already exists
    
    def _get_blob_client(self, blob_name: str) -> BlobClient:
        """Get blob client for a specific blob"""
        return self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
    
    def _get_container_client(self) -> ContainerClient:
        """Get container client"""
        return self.blob_service_client.get_container_client(self.container_name)
    
    def _blob_exists(self, blob_name: str) -> bool:
        """Check if blob exists"""
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False
    
    def _read_json_blob(self, blob_name: str, default=None):
        """Read and parse JSON blob"""
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_data = blob_client.download_blob().readall()
            return json.loads(blob_data.decode('utf-8'))
        except Exception:
            return default if default is not None else {}
    
    def _write_json_blob(self, blob_name: str, data):
        """Write JSON data to blob"""
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        blob_client = self._get_blob_client(blob_name)
        blob_client.upload_blob(json_data.encode('utf-8'), overwrite=True)
    
    def _read_text_blob(self, blob_name: str) -> Optional[str]:
        """Read text blob"""
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_data = blob_client.download_blob().readall()
            return blob_data.decode('utf-8')
        except Exception:
            return None
    
    def _write_text_blob(self, blob_name: str, content: str):
        """Write text blob"""
        blob_client = self._get_blob_client(blob_name)
        blob_client.upload_blob(content.encode('utf-8'), overwrite=True)
    
    def _list_blobs_with_prefix(self, prefix: str) -> List[str]:
        """List all blobs with a given prefix"""
        container_client = self._get_container_client()
        blob_names = []
        
        for blob in container_client.list_blobs(name_starts_with=prefix):
            blob_names.append(blob.name)
        
        return blob_names
    
    def create_or_update_project(self, project_id: str, project_name: str) -> bool:
        """Create or update a project. Returns True if new, False if updated."""
        # Load existing project mapping
        projects = self.load_project_mapping()
        is_new = project_id not in projects
        projects[project_id] = project_name
        
        # Write back to file in pipe-separated format with active flag
        content = ""
        for pid, name in projects.items():
            content += f"{pid}|{name}|1\n"
        
        self._write_text_blob("proj_mapping.txt", content)
        return is_new
    
    def load_project_mapping(self) -> Dict[str, str]:
        """Load project mapping from blob storage"""
        content = self._read_text_blob("proj_mapping.txt")
        projects = {}
        
        if content:
            for line in content.splitlines():
                line = line.strip()
                if line:
                    # Support both tab-separated (old) and pipe-separated (new) formats
                    if '|' in line:
                        parts = line.split('|', 2)
                        if len(parts) >= 2:
                            project_id, name = parts[0].strip(), parts[1].strip()
                            projects[project_id] = name
                    elif '\t' in line:
                        project_id, name = line.split('\t', 1)
                        projects[project_id.strip()] = name.strip()
        
        return projects
    
    def load_faqs(self, project_id: str) -> List[FAQEntry]:
        """Load FAQ entries for a project"""
        blob_name = f"{project_id}/{project_id}.faq.json"
        faq_data = self._read_json_blob(blob_name, [])
        return [FAQEntry.from_dict(item) for item in faq_data]
    
    def load_kb_entries(self, project_id: str) -> List[KBEntry]:
        """Load KB entries for a project"""
        blob_name = f"{project_id}/{project_id}.kb.json"
        kb_data = self._read_json_blob(blob_name, [])
        return [KBEntry.from_dict(item) for item in kb_data]
    
    def save_faqs(self, project_id: str, faqs: List[FAQEntry]):
        """Save FAQ entries to blob storage"""
        blob_name = f"{project_id}/{project_id}.faq.json"
        data = [faq.to_dict() for faq in faqs]
        self._write_json_blob(blob_name, data)
    
    def save_kb_entries(self, project_id: str, kb_entries: List[KBEntry]):
        """Save KB entries to blob storage"""
        blob_name = f"{project_id}/{project_id}.kb.json"
        data = [kb.to_dict() for kb in kb_entries]
        self._write_json_blob(blob_name, data)
    
    def upsert_faqs(self, project_id: str, new_faqs: List[FAQEntry], replace: bool = False) -> Tuple[List[str], List[str]]:
        """Upsert FAQ entries. Returns (created_ids, updated_ids)"""
        existing_faqs = self.load_faqs(project_id) if not replace else []
        existing_by_id = {faq.id: faq for faq in existing_faqs}
        
        created_ids = []
        updated_ids = []
        
        for faq in new_faqs:
            if faq.id in existing_by_id:
                updated_ids.append(faq.id)
            else:
                created_ids.append(faq.id)
            existing_by_id[faq.id] = faq
        
        # Save all FAQs
        all_faqs = list(existing_by_id.values())
        self.save_faqs(project_id, all_faqs)
        
        return created_ids, updated_ids
    
    def upsert_kb_entries(self, project_id: str, new_entries: List[KBEntry], replace: bool = False) -> Tuple[List[str], List[str]]:
        """Upsert KB entries. Returns (created_ids, updated_ids)"""
        existing_entries = self.load_kb_entries(project_id) if not replace else []
        existing_by_id = {entry.id: entry for entry in existing_entries}
        
        created_ids = []
        updated_ids = []
        
        for entry in new_entries:
            if entry.id in existing_by_id:
                updated_ids.append(entry.id)
            else:
                created_ids.append(entry.id)
            existing_by_id[entry.id] = entry
        
        # Save all entries
        all_entries = list(existing_by_id.values())
        self.save_kb_entries(project_id, all_entries)
        
        return created_ids, updated_ids
    
    def save_attachment(self, project_id: str, filename: str, content: bytes) -> str:
        """Save attachment file to blob storage. Returns the blob URL."""
        blob_name = f"{project_id}/attachments/{filename}"
        blob_client = self._get_blob_client(blob_name)
        
        # Set content type
        content_type, _ = mimetypes.guess_type(filename)
        content_settings = {"content_type": content_type or "application/octet-stream"}
        
        blob_client.upload_blob(content, overwrite=True, content_settings=content_settings)
        return blob_name
    
    def get_attachment(self, project_id: str, filename: str) -> Optional[bytes]:
        """Get attachment file content"""
        blob_name = f"{project_id}/attachments/{filename}"
        try:
            blob_client = self._get_blob_client(blob_name)
            return blob_client.download_blob().readall()
        except Exception:
            return None
    
    def delete_attachment(self, project_id: str, filename: str) -> bool:
        """Delete attachment file. Returns True if deleted, False if not found."""
        blob_name = f"{project_id}/attachments/{filename}"
        try:
            blob_client = self._get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except Exception:
            return False
    
    def list_attachments(self, project_id: str) -> List[str]:
        """List all attachment filenames for a project"""
        prefix = f"{project_id}/attachments/"
        blob_names = self._list_blobs_with_prefix(prefix)
        
        # Extract just the filename from the full blob path
        filenames = []
        for blob_name in blob_names:
            if blob_name.startswith(prefix):
                filename = blob_name[len(prefix):]
                if filename:  # Make sure it's not empty
                    filenames.append(filename)
        
        return filenames
    
    def delete_faq(self, project_id: str, faq_id: str) -> bool:
        """Delete a FAQ entry by ID. Returns True if deleted, False if not found."""
        existing_faqs = self.load_faqs(project_id)
        existing_by_id = {faq.id: faq for faq in existing_faqs}
        
        if faq_id not in existing_by_id:
            return False
        
        # Get the FAQ to check for source files
        faq_to_delete = existing_by_id[faq_id]
        
        # Remove the FAQ
        del existing_by_id[faq_id]
        
        # Save remaining FAQs
        remaining_faqs = list(existing_by_id.values())
        self.save_faqs(project_id, remaining_faqs)
        
        # Clean up associated source file if it exists
        if faq_to_delete.source_file:
            self.delete_attachment(project_id, faq_to_delete.source_file)
        
        # Also try to clean up potential FAQ attachment files (multiple formats)
        potential_files = [
            f"{faq_id}-faq.txt",
            f"{faq_id}-faq.docx",
            f"{faq_id}-faq.pdf"
        ]
        for filename in potential_files:
            self.delete_attachment(project_id, filename)
        
        return True
    
    def delete_kb_entry(self, project_id: str, kb_id: str) -> bool:
        """Delete a KB entry by ID. Returns True if deleted, False if not found."""
        existing_entries = self.load_kb_entries(project_id)
        existing_by_id = {entry.id: entry for entry in existing_entries}
        
        if kb_id not in existing_by_id:
            return False
        
        # Get the KB entry to check for source files
        kb_to_delete = existing_by_id[kb_id]
        
        # Remove the KB entry
        del existing_by_id[kb_id]
        
        # Save remaining entries
        remaining_entries = list(existing_by_id.values())
        self.save_kb_entries(project_id, remaining_entries)
        
        # Clean up associated source file if it exists
        if kb_to_delete.source_file:
            self.delete_attachment(project_id, kb_to_delete.source_file)
        
        # Also try to clean up potential KB attachment files (multiple formats)
        potential_files = [
            f"{kb_id}-kb.txt",
            f"{kb_id}-kb.docx", 
            f"{kb_id}-kb.pdf"
        ]
        for filename in potential_files:
            self.delete_attachment(project_id, filename)
        
        return True
    
    def get_faq_by_id(self, project_id: str, faq_id: str) -> Optional[FAQEntry]:
        """Get a specific FAQ by ID"""
        faqs = self.load_faqs(project_id)
        for faq in faqs:
            if faq.id == faq_id:
                return faq
        return None
    
    def get_kb_entry_by_id(self, project_id: str, kb_id: str) -> Optional[KBEntry]:
        """Get a specific KB entry by ID"""
        entries = self.load_kb_entries(project_id)
        for entry in entries:
            if entry.id == kb_id:
                return entry
        return None
    
    def get_index_metadata(self, project_id: str) -> Dict:
        """Get index metadata for a project"""
        blob_name = f"{project_id}/index/meta.json"
        return self._read_json_blob(blob_name, {"error": "No index metadata found"})
    
    def save_index_metadata(self, project_id: str, metadata: Dict):
        """Save index metadata for a project"""
        blob_name = f"{project_id}/index/meta.json"
        self._write_json_blob(blob_name, metadata)