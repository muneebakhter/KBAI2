#!/usr/bin/env python3
"""
Storage interface abstraction for KBAI - supports multiple backends.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from kb_api.models import FAQEntry, KBEntry


class StorageInterface(ABC):
    """Abstract interface for storage backends"""
    
    @abstractmethod
    def create_or_update_project(self, project_id: str, project_name: str) -> bool:
        """Create or update a project. Returns True if new, False if updated."""
        pass
    
    @abstractmethod
    def load_project_mapping(self) -> Dict[str, str]:
        """Load project mapping from storage"""
        pass
    
    @abstractmethod
    def load_faqs(self, project_id: str) -> List[FAQEntry]:
        """Load FAQ entries for a project"""
        pass
    
    @abstractmethod
    def load_kb_entries(self, project_id: str) -> List[KBEntry]:
        """Load KB entries for a project"""
        pass
    
    @abstractmethod
    def save_faqs(self, project_id: str, faqs: List[FAQEntry]):
        """Save FAQ entries to storage"""
        pass
    
    @abstractmethod
    def save_kb_entries(self, project_id: str, kb_entries: List[KBEntry]):
        """Save KB entries to storage"""
        pass
    
    @abstractmethod
    def upsert_faqs(self, project_id: str, new_faqs: List[FAQEntry], replace: bool = False) -> Tuple[List[str], List[str]]:
        """Upsert FAQ entries. Returns (created_ids, updated_ids)"""
        pass
    
    @abstractmethod
    def upsert_kb_entries(self, project_id: str, new_entries: List[KBEntry], replace: bool = False) -> Tuple[List[str], List[str]]:
        """Upsert KB entries. Returns (created_ids, updated_ids)"""
        pass
    
    @abstractmethod
    def save_attachment(self, project_id: str, filename: str, content: bytes) -> str:
        """Save attachment file. Returns the file path/URL."""
        pass
    
    @abstractmethod
    def delete_faq(self, project_id: str, faq_id: str) -> bool:
        """Delete a FAQ entry by ID. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    def delete_kb_entry(self, project_id: str, kb_id: str) -> bool:
        """Delete a KB entry by ID. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    def get_faq_by_id(self, project_id: str, faq_id: str) -> Optional[FAQEntry]:
        """Get a specific FAQ by ID"""
        pass
    
    @abstractmethod
    def get_kb_entry_by_id(self, project_id: str, kb_id: str) -> Optional[KBEntry]:
        """Get a specific KB entry by ID"""
        pass
    
    @abstractmethod
    def get_index_metadata(self, project_id: str) -> Dict:
        """Get index metadata for a project"""
        pass
    
    @abstractmethod
    def get_attachment(self, project_id: str, filename: str) -> Optional[bytes]:
        """Get attachment file content"""
        pass
    
    @abstractmethod
    def delete_attachment(self, project_id: str, filename: str) -> bool:
        """Delete attachment file. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    def list_attachments(self, project_id: str) -> List[str]:
        """List all attachment filenames for a project"""
        pass
    
    @abstractmethod
    def save_index_metadata(self, project_id: str, metadata: Dict):
        """Save index metadata for a project"""
        pass