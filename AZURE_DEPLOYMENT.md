# KBAI Azure Cloud Deployment Guide

This guide helps you deploy KBAI with scalable Azure storage backends for multi-instance production environments.

## 🚀 Quick Start

### 1. Choose Your Storage Strategy

| Storage Backend | Use Case | Scaling | Performance |
|----------------|----------|---------|-------------|
| **Azure File Share** | Drop-in replacement for local files | ⭐⭐⭐ | ⭐⭐ |
| **Azure Blob Storage** | Large files, attachments, indexes | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Azure CosmosDB** | High-performance structured data | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Hybrid** | Production-optimized combination | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### 2. Deploy Infrastructure

```bash
# Login to Azure
az login

# Create resource group
az group create --name kbai-production --location "East US"

# Deploy with Azure File Share (simplest)
az deployment group create \
  --resource-group kbai-production \
  --template-file azure-templates/main.json \
  --parameters \
    projectName="mykbai" \
    storageBackend="azure_fileshare" \
    openaiApiKey="your-openai-api-key"

# Deploy with CosmosDB (high performance)
az deployment group create \
  --resource-group kbai-production \
  --template-file azure-templates/main.json \
  --parameters \
    projectName="mykbai" \
    storageBackend="cosmosdb" \
    openaiApiKey="your-openai-api-key" \
    enableFreeTier=true
```

### 3. Configure Your Application

The ARM templates automatically configure your App Service, but you can also run KBAI locally or in containers:

```bash
# Install Azure dependencies
pip install -r requirements-azure.txt

# Configure environment
export STORAGE_TYPE=azure_fileshare
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."

# Run locally
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   KBAI App #1   │    │   KBAI App #2   │    │   KBAI App #N   │
│ (Azure App Svc) │    │ (Azure App Svc) │    │ (Azure App Svc) │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
              ┌──────────────────────────────────┐
              │        Shared Storage            │
              │                                  │
      ┌───────┴────────┐  ┌─────────────┐  ┌────┴─────────┐
      │ Azure File Share│  │ Azure Blob  │  │   CosmosDB   │
      │   (Projects,    │  │ (Attachments│  │ (Structured  │
      │  Configs, etc.) │  │ Large Files)│  │    Data)     │
      └────────────────┘  └─────────────┘  └──────────────┘
```

## 📊 Storage Backend Details

### Azure File Share Storage
**Best for**: Teams transitioning from local file storage

```env
STORAGE_TYPE=azure_fileshare
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=...
AZURE_FILESHARE_NAME=kbai-data
```

**Features**:
- ✅ SMB/NFS network protocol support
- ✅ Easy migration from local files
- ✅ Snapshot and backup capabilities
- ⚠️ Moderate performance for high-concurrency scenarios

### Azure Blob Storage
**Best for**: Large files, attachments, and media content

```env
STORAGE_TYPE=azure_blob
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=...
AZURE_BLOB_CONTAINER_NAME=kbai-data
```

**Features**:
- ✅ Optimized for large files and attachments
- ✅ Built-in CDN integration
- ✅ Lifecycle management for cost optimization
- ✅ High throughput and concurrent access
- ⚠️ REST API access only (no direct file system mounting)

### Azure CosmosDB
**Best for**: High-performance, globally distributed applications

```env
STORAGE_TYPE=cosmosdb
COSMOS_ENDPOINT=https://your-cosmosdb-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-primary-key
COSMOS_DATABASE_NAME=kbai-db
```

**Features**:
- ✅ 99.999% availability SLA
- ✅ Global distribution and multi-region writes
- ✅ Multiple consistency levels
- ✅ Automatic scaling and partitioning
- ⚠️ Learning curve for NoSQL data modeling
- ⚠️ Higher cost for small workloads

### Hybrid Configuration
**Best for**: Production deployments requiring optimal performance

```env
STORAGE_TYPE=hybrid
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=...
COSMOS_ENDPOINT=https://your-cosmosdb-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-primary-key
```

Uses:
- **CosmosDB** for structured data (projects, FAQs, KB entries)
- **Blob Storage** for attachments and large files
- **File Share** for shared configuration and search indexes

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `STORAGE_TYPE` | Storage backend type | No | `file` |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection string | For Azure backends | - |
| `AZURE_FILESHARE_NAME` | File share name | No | `kbai-data` |
| `AZURE_BLOB_CONTAINER_NAME` | Blob container name | No | `kbai-data` |
| `COSMOS_ENDPOINT` | CosmosDB endpoint URL | For CosmosDB | - |
| `COSMOS_KEY` | CosmosDB primary key | For CosmosDB | - |
| `COSMOS_DATABASE_NAME` | CosmosDB database name | No | `kbai-db` |

### Application Settings (Azure App Service)

When deploying to Azure App Service, configure these in the Application Settings:

```json
{
  "STORAGE_TYPE": "azure_fileshare",
  "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=...",
  "OPENAI_API_KEY": "your-openai-api-key",
  "AUTH_SIGNING_KEY": "your-jwt-signing-key"
}
```

## 🔄 Migration Guide

### From Local File Storage to Azure

1. **Backup your data**:
   ```bash
   tar -czf kbai-backup.tar.gz data/
   ```

2. **Deploy Azure infrastructure**:
   ```bash
   az deployment group create --resource-group kbai-rg --template-file azure-templates/main.json
   ```

3. **Migrate data**:
   ```bash
   # Update environment variables
   export STORAGE_TYPE=azure_fileshare
   export AZURE_STORAGE_CONNECTION_STRING="..."
   
   # Run migration script
   python examples/storage_backends.py
   ```

4. **Test and validate**:
   ```bash
   curl https://your-app.azurewebsites.net/v1/projects
   ```

### Between Azure Storage Types

You can switch between Azure storage backends by:

1. Exporting data from current backend
2. Updating `STORAGE_TYPE` environment variable  
3. Importing data to new backend
4. Updating application configuration

## 📈 Scaling and Performance

### Horizontal Scaling

```bash
# Scale App Service instances
az appservice plan update --number-of-workers 5 --name your-app-service-plan --resource-group kbai-rg

# All storage backends support concurrent access from multiple instances
```

### Performance Optimization

1. **Use Premium Storage** for high-IOPS workloads
2. **Enable CDN** for static content and attachments
3. **Configure Application Insights** for monitoring
4. **Use connection pooling** for database connections

### Cost Optimization

| Environment | Recommended Configuration |
|-------------|--------------------------|
| **Development** | File storage or CosmosDB free tier |
| **Staging** | Azure File Share with Standard storage |
| **Production** | Hybrid configuration with Premium storage |

## 🔒 Security Best Practices

### Authentication
- Use **Managed Identity** for Azure service authentication
- Store secrets in **Azure Key Vault**
- Implement **RBAC** for fine-grained access control

### Network Security
- Configure **private endpoints** for Azure services
- Use **virtual network integration** for App Service
- Enable **firewall rules** on storage accounts

### Data Protection
- Enable **encryption at rest** for all storage services
- Use **HTTPS only** for all communications
- Implement **backup and disaster recovery** strategies

## 🚨 Troubleshooting

### Common Issues

1. **Storage Connection Errors**:
   ```bash
   # Verify connection string format
   echo $AZURE_STORAGE_CONNECTION_STRING
   
   # Test connectivity
   az storage account show --name yourstorageaccount
   ```

2. **CosmosDB Throttling**:
   ```bash
   # Check RU consumption
   az cosmosdb database throughput show --account-name your-account --name kbai-db
   
   # Scale throughput
   az cosmosdb database throughput update --account-name your-account --name kbai-db --throughput 1000
   ```

3. **App Service Deployment Issues**:
   ```bash
   # Check logs
   az webapp log tail --name your-app --resource-group kbai-rg
   
   # Restart application
   az webapp restart --name your-app --resource-group kbai-rg
   ```

### Monitoring and Alerting

Set up monitoring for:
- **Application performance** (Application Insights)
- **Storage metrics** (Azure Monitor)
- **Cost tracking** (Azure Cost Management)
- **Security alerts** (Azure Security Center)

## 📚 Additional Resources

- [Azure Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/)
- [Azure CosmosDB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
- [ARM Template Reference](https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/)

## 🆘 Support

For issues specific to KBAI Azure deployment:
1. Check the application logs in Azure Portal
2. Review the ARM template outputs for configuration details
3. Validate environment variables and connection strings
4. Test storage connectivity using the examples in `examples/storage_backends.py`