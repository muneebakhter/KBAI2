#!/usr/bin/env python3
"""
Example usage of KBAI with different Azure storage backends.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb_api.storage_factory import create_storage_backend
from kb_api.models import FAQEntry, KBEntry

def example_file_storage():
    """Example using local file storage (default)"""
    print("=== File Storage Example ===")
    
    storage = create_storage_backend("file", "./example_data")
    
    # Create a project
    storage.create_or_update_project("demo", "Demo Project")
    
    # Add some FAQs
    faq = FAQEntry(
        id="faq1",
        question="What is KBAI?",
        answer="KBAI is a Knowledge Base AI system for enterprise document management.",
        source_file=None
    )
    storage.save_faqs("demo", [faq])
    
    # Load and display
    faqs = storage.load_faqs("demo")
    print(f"Loaded {len(faqs)} FAQs")
    print(f"FAQ: {faqs[0].question}")


def example_azure_fileshare():
    """Example using Azure File Share storage"""
    print("\n=== Azure File Share Example ===")
    
    # This would use real Azure connection string in production
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if not connection_string:
        print("❌ AZURE_STORAGE_CONNECTION_STRING not set, skipping example")
        return
        
    try:
        storage = create_storage_backend(
            storage_type="azure_fileshare",
            azure_storage_connection_string=connection_string
        )
        
        # Same API as file storage
        storage.create_or_update_project("demo", "Demo Project")
        projects = storage.load_project_mapping()
        print(f"✅ Azure File Share working. Projects: {projects}")
        
    except ImportError:
        print("❌ Azure File Share SDK not installed. Run: pip install azure-storage-file-share")
    except Exception as e:
        print(f"❌ Azure File Share error: {e}")


def example_cosmosdb():
    """Example using Azure CosmosDB storage"""
    print("\n=== Azure CosmosDB Example ===")
    
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    
    if not endpoint or not key:
        print("❌ COSMOS_ENDPOINT or COSMOS_KEY not set, skipping example")
        return
        
    try:
        storage = create_storage_backend(
            storage_type="cosmosdb",
            cosmos_endpoint=endpoint,
            cosmos_key=key
        )
        
        # Same API as file storage
        storage.create_or_update_project("demo", "Demo Project")
        projects = storage.load_project_mapping()
        print(f"✅ CosmosDB working. Projects: {projects}")
        
    except ImportError:
        print("❌ CosmosDB SDK not installed. Run: pip install azure-cosmos")
    except Exception as e:
        print(f"❌ CosmosDB error: {e}")


def example_environment_based():
    """Example using environment variables for configuration"""
    print("\n=== Environment-Based Configuration Example ===")
    
    # This reads STORAGE_TYPE and related environment variables
    from kb_api.storage_factory import create_storage_from_env
    
    storage = create_storage_from_env("./example_data")
    storage_type = type(storage).__name__
    print(f"✅ Created storage backend: {storage_type}")
    
    # Test basic functionality
    storage.create_or_update_project("env_demo", "Environment Demo Project")
    projects = storage.load_project_mapping()
    print(f"Projects: {projects}")


if __name__ == "__main__":
    print("🚀 KBAI Storage Backend Examples\n")
    
    # Always works
    example_file_storage()
    example_environment_based()
    
    # Azure examples (require configuration)
    example_azure_fileshare()
    example_cosmosdb()
    
    print("\n✅ Examples completed!")
    print("\nTo use Azure storage backends:")
    print("1. Install Azure SDKs: pip install -r requirements-azure.txt")
    print("2. Set environment variables (see .env.example)")
    print("3. Deploy infrastructure using ARM templates in azure-templates/")