#!/usr/bin/env python3
"""
Simple file storage manager for testing
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from kb_api.models import FAQEntry, KBEntry


class FileStorageManager:
    """Simple file-based storage for testing"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def create_or_update_project(self, project_id: str, project_name: str) -> bool:
        """Create or update a project. Returns True if new, False if updated."""
        # Create project directory
        project_dir = self.base_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Create attachments directory
        attachments_dir = project_dir / "attachments"
        attachments_dir.mkdir(exist_ok=True)
        
        # Update project mapping
        mapping_file = self.base_dir / "proj_mapping.txt"
        projects = self.load_project_mapping()
        
        is_new = project_id not in projects
        projects[project_id] = project_name
        
        # Write back to file in pipe-separated format with active flag
        with open(mapping_file, 'w', encoding='utf-8') as f:
            for pid, name in projects.items():
                f.write(f"{pid}|{name}|1\n")
        
        return is_new
    
    def load_project_mapping(self) -> Dict[str, str]:
        """Load project mapping from file"""
        mapping_file = self.base_dir / "proj_mapping.txt"
        projects = {}
        
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
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
        faq_file = self.base_dir / project_id / f"{project_id}.faq.json"
        if not faq_file.exists():
            return []
        
        with open(faq_file, 'r', encoding='utf-8') as f:
            faq_data = json.load(f)
            return [FAQEntry.from_dict(item) for item in faq_data]
    
    def load_kb_entries(self, project_id: str) -> List[KBEntry]:
        """Load KB entries for a project"""
        kb_file = self.base_dir / project_id / f"{project_id}.kb.json"
        if not kb_file.exists():
            return []
        
        with open(kb_file, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
            return [KBEntry.from_dict(item) for item in kb_data]
    
    def save_faqs(self, project_id: str, faqs: List[FAQEntry]):
        """Save FAQ entries to file"""
        faq_file = self.base_dir / project_id / f"{project_id}.faq.json"
        with open(faq_file, 'w', encoding='utf-8') as f:
            json.dump([faq.to_dict() for faq in faqs], f, indent=2, ensure_ascii=False)
    
    def save_kb_entries(self, project_id: str, kb_entries: List[KBEntry]):
        """Save KB entries to file"""
        kb_file = self.base_dir / project_id / f"{project_id}.kb.json"
        with open(kb_file, 'w', encoding='utf-8') as f:
            json.dump([kb.to_dict() for kb in kb_entries], f, indent=2, ensure_ascii=False)
    
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
        """Save attachment file. Returns the file path."""
        attachments_dir = self.base_dir / project_id / "attachments"
        attachments_dir.mkdir(exist_ok=True)
        
        file_path = attachments_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return str(file_path)
    
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
            attachments_dir = self.base_dir / project_id / "attachments"
            source_file_path = attachments_dir / faq_to_delete.source_file
            if source_file_path.exists():
                source_file_path.unlink()
        
        # Also try to clean up potential FAQ attachment files (multiple formats)
        attachments_dir = self.base_dir / project_id / "attachments"
        potential_files = [
            attachments_dir / f"{faq_id}-faq.txt",
            attachments_dir / f"{faq_id}-faq.docx",
            attachments_dir / f"{faq_id}-faq.pdf"
        ]
        for file_path in potential_files:
            if file_path.exists():
                file_path.unlink()
        
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
            attachments_dir = self.base_dir / project_id / "attachments"
            source_file_path = attachments_dir / kb_to_delete.source_file
            if source_file_path.exists():
                source_file_path.unlink()
        
        # Also try to clean up potential KB attachment files (multiple formats)
        attachments_dir = self.base_dir / project_id / "attachments"
        potential_files = [
            attachments_dir / f"{kb_id}-kb.txt",
            attachments_dir / f"{kb_id}-kb.docx", 
            attachments_dir / f"{kb_id}-kb.pdf"
        ]
        for file_path in potential_files:
            if file_path.exists():
                file_path.unlink()
        
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
        meta_file = self.base_dir / project_id / "index" / "meta.json"
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"error": "No index metadata found"}