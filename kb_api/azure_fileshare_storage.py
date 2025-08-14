#!/usr/bin/env python3
"""
Azure File Share storage backend for KBAI.
"""

import os
import json
from pathlib import Path, PurePath
from typing import List, Dict, Optional, Tuple
from kb_api.models import FAQEntry, KBEntry
from kb_api.storage_interface import StorageInterface

try:
    from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient, ShareServiceClient
    HAS_AZURE_STORAGE = True
except ImportError:
    HAS_AZURE_STORAGE = False


class AzureFileShareStorage(StorageInterface):
    """Azure File Share storage backend"""
    
    def __init__(self, connection_string: str, share_name: str = "kbai-data"):
        if not HAS_AZURE_STORAGE:
            raise ImportError("azure-storage-file-share package is required for Azure File Share storage")
        
        self.connection_string = connection_string
        self.share_name = share_name
        
        # Initialize Azure File Share client
        self.service_client = ShareServiceClient.from_connection_string(connection_string)
        
        # Ensure share exists
        try:
            self.service_client.create_share(share_name)
        except Exception:
            pass  # Share already exists
    
    def _get_file_client(self, file_path: str) -> ShareFileClient:
        """Get file client for a specific file"""
        return ShareFileClient.from_connection_string(
            self.connection_string,
            share_name=self.share_name,
            file_path=file_path
        )
    
    def _get_directory_client(self, directory_path: str) -> ShareDirectoryClient:
        """Get directory client for a specific directory"""
        return ShareDirectoryClient.from_connection_string(
            self.connection_string,
            share_name=self.share_name,
            directory_path=directory_path
        )
    
    def _ensure_directory(self, directory_path: str):
        """Ensure directory exists in Azure File Share"""
        try:
            dir_client = self._get_directory_client(directory_path)
            dir_client.create_directory()
        except Exception:
            pass  # Directory already exists or parent doesn't exist
        
        # Ensure parent directories exist
        parent = str(PurePath(directory_path).parent)
        if parent != "." and parent != directory_path:
            self._ensure_directory(parent)
            try:
                dir_client = self._get_directory_client(directory_path)
                dir_client.create_directory()
            except Exception:
                pass
    
    def _file_exists(self, file_path: str) -> bool:
        """Check if file exists in Azure File Share"""
        try:
            file_client = self._get_file_client(file_path)
            file_client.get_file_properties()
            return True
        except Exception:
            return False
    
    def _read_json_file(self, file_path: str, default=None):
        """Read and parse JSON file from Azure File Share"""
        try:
            file_client = self._get_file_client(file_path)
            data = file_client.download_file().readall()
            return json.loads(data.decode('utf-8'))
        except Exception:
            return default if default is not None else {}
    
    def _write_json_file(self, file_path: str, data):
        """Write JSON data to Azure File Share"""
        # Ensure directory exists
        directory = str(PurePath(file_path).parent)
        if directory != ".":
            self._ensure_directory(directory)
        
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        file_client = self._get_file_client(file_path)
        file_client.upload_file(json_data.encode('utf-8'))
    
    def _read_text_file(self, file_path: str) -> Optional[str]:
        """Read text file from Azure File Share"""
        try:
            file_client = self._get_file_client(file_path)
            data = file_client.download_file().readall()
            return data.decode('utf-8')
        except Exception:
            return None
    
    def _write_text_file(self, file_path: str, content: str):
        """Write text file to Azure File Share"""
        # Ensure directory exists
        directory = str(PurePath(file_path).parent)
        if directory != ".":
            self._ensure_directory(directory)
        
        file_client = self._get_file_client(file_path)
        file_client.upload_file(content.encode('utf-8'))
    
    def create_or_update_project(self, project_id: str, project_name: str) -> bool:
        """Create or update a project. Returns True if new, False if updated."""
        # Create project directory
        self._ensure_directory(project_id)
        
        # Create attachments directory
        self._ensure_directory(f"{project_id}/attachments")
        
        # Update project mapping
        projects = self.load_project_mapping()
        is_new = project_id not in projects
        projects[project_id] = project_name
        
        # Write back to file in pipe-separated format with active flag
        content = ""
        for pid, name in projects.items():
            content += f"{pid}|{name}|1\n"
        
        self._write_text_file("proj_mapping.txt", content)
        return is_new
    
    def load_project_mapping(self) -> Dict[str, str]:
        """Load project mapping from Azure File Share"""
        content = self._read_text_file("proj_mapping.txt")
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
        faq_data = self._read_json_file(f"{project_id}/{project_id}.faq.json", [])
        return [FAQEntry.from_dict(item) for item in faq_data]
    
    def load_kb_entries(self, project_id: str) -> List[KBEntry]:
        """Load KB entries for a project"""
        kb_data = self._read_json_file(f"{project_id}/{project_id}.kb.json", [])
        return [KBEntry.from_dict(item) for item in kb_data]
    
    def save_faqs(self, project_id: str, faqs: List[FAQEntry]):
        """Save FAQ entries to Azure File Share"""
        data = [faq.to_dict() for faq in faqs]
        self._write_json_file(f"{project_id}/{project_id}.faq.json", data)
    
    def save_kb_entries(self, project_id: str, kb_entries: List[KBEntry]):
        """Save KB entries to Azure File Share"""
        data = [kb.to_dict() for kb in kb_entries]
        self._write_json_file(f"{project_id}/{project_id}.kb.json", data)
    
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
        """Save attachment file to Azure File Share. Returns the file path."""
        file_path = f"{project_id}/attachments/{filename}"
        
        # Ensure directory exists
        self._ensure_directory(f"{project_id}/attachments")
        
        file_client = self._get_file_client(file_path)
        file_client.upload_file(content)
        
        return file_path
    
    def get_attachment(self, project_id: str, filename: str) -> Optional[bytes]:
        """Get attachment file content"""
        try:
            file_client = self._get_file_client(f"{project_id}/attachments/{filename}")
            return file_client.download_file().readall()
        except Exception:
            return None
    
    def delete_attachment(self, project_id: str, filename: str) -> bool:
        """Delete attachment file. Returns True if deleted, False if not found."""
        try:
            file_client = self._get_file_client(f"{project_id}/attachments/{filename}")
            file_client.delete_file()
            return True
        except Exception:
            return False
    
    def list_attachments(self, project_id: str) -> List[str]:
        """List all attachment filenames for a project"""
        try:
            dir_client = self._get_directory_client(f"{project_id}/attachments")
            files = []
            for item in dir_client.list_directories_and_files():
                if not item['is_directory']:
                    files.append(item['name'])
            return files
        except Exception:
            return []
    
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
        return self._read_json_file(f"{project_id}/index/meta.json", {"error": "No index metadata found"})
    
    def save_index_metadata(self, project_id: str, metadata: Dict):
        """Save index metadata for a project"""
        self._write_json_file(f"{project_id}/index/meta.json", metadata)