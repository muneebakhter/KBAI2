# KBAI Azure Deployment Templates

This directory contains Azure Resource Manager (ARM) templates for deploying KBAI in Azure with scalable storage options.

## Template Overview

### 1. Main Template (`main.json`)
The primary deployment template that orchestrates all other templates. It supports multiple storage backend configurations:

- **Azure File Share**: Network file share for multi-instance deployments
- **Azure Blob Storage**: Object storage for large files and attachments  
- **CosmosDB**: NoSQL database for structured data (projects, FAQs, KB entries)
- **Hybrid**: Combination of multiple storage backends

### 2. Storage Account Template (`storage-account.json`)
Creates Azure Storage Account with:
- File Share for network-attached storage
- Blob Container for object storage
- Appropriate security and access configurations

### 3. CosmosDB Template (`cosmosdb.json`)
Creates Azure CosmosDB with:
- SQL API database and containers
- Optimized partition keys for KBAI data model
- Configurable consistency levels and throughput

### 4. App Service Template (`app-service.json`)
Creates Azure App Service to host KBAI application with:
- Linux-based App Service Plan
- Python 3.11 runtime
- Environment variables for storage configuration
- Source code deployment from Git repository

## Quick Deployment

### Option 1: Deploy via Azure Portal

1. **Upload templates** to Azure Portal or use Azure CLI
2. **Configure parameters** based on your requirements
3. **Deploy** using the main template

### Option 2: Deploy via Azure CLI

```bash
# Login to Azure
az login

# Create resource group
az group create --name kbai-rg --location "East US"

# Deploy with Azure File Share storage
az deployment group create \
  --resource-group kbai-rg \
  --template-file azure-templates/main.json \
  --parameters \
    projectName="mykbai" \
    storageBackend="azure_fileshare" \
    openaiApiKey="your-openai-api-key" \
    location="East US"

# Deploy with CosmosDB storage
az deployment group create \
  --resource-group kbai-rg \
  --template-file azure-templates/main.json \
  --parameters \
    projectName="mykbai" \
    storageBackend="cosmosdb" \
    openaiApiKey="your-openai-api-key" \
    enableFreeTier=true \
    location="East US"

# Deploy infrastructure only (no App Service)
az deployment group create \
  --resource-group kbai-rg \
  --template-file azure-templates/main.json \
  --parameters \
    projectName="mykbai" \
    storageBackend="hybrid" \
    deployAppService=false \
    location="East US"
```

### Option 3: Deploy via PowerShell

```powershell
# Connect to Azure
Connect-AzAccount

# Create resource group
New-AzResourceGroup -Name "kbai-rg" -Location "East US"

# Deploy with parameters
New-AzResourceGroupDeployment `
  -ResourceGroupName "kbai-rg" `
  -TemplateFile "azure-templates/main.json" `
  -projectName "mykbai" `
  -storageBackend "azure_fileshare" `
  -openaiApiKey "your-openai-api-key" `
  -location "East US"
```

## Storage Backend Options

### 1. Azure File Share (`azure_fileshare`)
**Best for**: Traditional multi-instance deployments requiring shared file access

**Features**:
- Network-attached storage accessible from multiple App Service instances
- SMB/NFS protocol support
- Good for lift-and-shift scenarios
- Automatic backup and versioning

**Configuration**:
```json
{
  "storageBackend": "azure_fileshare"
}
```

### 2. Azure Blob Storage (`azure_blob`)
**Best for**: Large files, attachments, and search indexes

**Features**:
- Object storage with REST API access
- Excellent for large files and media content
- Built-in CDN integration capability
- Lifecycle management for cost optimization

**Configuration**:
```json
{
  "storageBackend": "azure_blob"
}
```

### 3. CosmosDB (`cosmosdb`)
**Best for**: High-performance, globally distributed deployments

**Features**:
- NoSQL document database with global distribution
- Multiple consistency levels
- Automatic scaling and partitioning
- 99.999% availability SLA

**Configuration**:
```json
{
  "storageBackend": "cosmosdb",
  "enableFreeTier": true
}
```

### 4. Hybrid (`hybrid`)
**Best for**: Production deployments requiring optimal performance

**Features**:
- CosmosDB for structured data (projects, FAQs, KB entries)
- Blob Storage for attachments and large files
- File Share for shared configuration and indexes
- Best performance and scalability

**Configuration**:
```json
{
  "storageBackend": "hybrid"
}
```

## Template Parameters

### Main Template Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `projectName` | string | `kbai-{uniqueString}` | Project name prefix for all resources |
| `location` | string | Resource group location | Azure region for deployment |
| `storageBackend` | string | `azure_fileshare` | Storage backend type |
| `deployAppService` | bool | `true` | Whether to deploy App Service |
| `openaiApiKey` | string | `""` | OpenAI API key for AI features |
| `enableFreeTier` | bool | `false` | Enable CosmosDB free tier |

### Storage Account Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `storageAccountName` | string | Auto-generated | Storage account name |
| `skuName` | string | `Standard_LRS` | Storage account SKU |
| `fileShareName` | string | `kbai-data` | File share name |
| `blobContainerName` | string | `kbai-data` | Blob container name |

### CosmosDB Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cosmosAccountName` | string | Auto-generated | Cosmos account name |
| `consistencyLevel` | string | `Session` | Consistency level |
| `throughputPolicy` | string | `Autoscale` | Throughput policy |
| `enableFreeTier` | bool | `false` | Enable free tier |

## Post-Deployment Configuration

After deployment, configure your KBAI application:

1. **Set Environment Variables** in App Service:
   ```bash
   # The ARM template automatically sets these, but you can override:
   STORAGE_TYPE=azure_fileshare  # or azure_blob, cosmosdb
   AZURE_STORAGE_CONNECTION_STRING=<connection-string>
   COSMOS_ENDPOINT=<cosmos-endpoint>
   COSMOS_KEY=<cosmos-key>
   OPENAI_API_KEY=<your-api-key>
   ```

2. **Initialize Sample Data** (optional):
   ```bash
   # Connect to App Service via SSH or use deployment script
   python create_sample_data.py
   python prebuild_kb.py
   ```

3. **Access Your Application**:
   - Main API: `https://{your-app-name}.azurewebsites.net`
   - Admin Interface: `https://{your-app-name}.azurewebsites.net/admin`
   - API Documentation: `https://{your-app-name}.azurewebsites.net/docs`

## Scaling Considerations

### Horizontal Scaling
- **App Service**: Scale out with multiple instances
- **Storage**: All backends support concurrent access from multiple instances
- **Database**: CosmosDB provides automatic partitioning and scaling

### Performance Optimization
- Use **Premium Storage** for high-IOPS workloads
- Enable **CDN** for static content and attachments
- Configure **Application Insights** for monitoring
- Use **Azure Front Door** for global load balancing

## Cost Optimization

### Development/Testing
```json
{
  "storageBackend": "azure_fileshare",
  "skuName": "Standard_LRS",
  "enableFreeTier": true,
  "appServiceSku": "F1"
}
```

### Production
```json
{
  "storageBackend": "hybrid",
  "skuName": "Standard_ZRS",
  "enableFreeTier": false,
  "appServiceSku": "P1V2"
}
```

## Security Configuration

### Network Security
- **Storage Account**: Configure firewall rules and virtual network integration
- **CosmosDB**: Enable private endpoints and disable public access
- **App Service**: Use managed identity for authentication

### Access Control
- **RBAC**: Assign appropriate roles to users and applications
- **Key Vault**: Store sensitive configuration in Azure Key Vault
- **Managed Identity**: Use for Azure service authentication

## Monitoring and Observability

The deployed infrastructure includes:
- **Application Insights**: Application performance monitoring
- **Azure Monitor**: Infrastructure monitoring and alerting
- **Storage Analytics**: Storage performance and usage metrics
- **CosmosDB Metrics**: Database performance and cost tracking

## Troubleshooting

### Common Issues

1. **Storage Connection Issues**:
   - Verify connection string format
   - Check storage account firewall rules
   - Ensure managed identity has appropriate permissions

2. **CosmosDB Connection Issues**:
   - Verify endpoint URL and key
   - Check consistency level configuration
   - Monitor request units (RU) consumption

3. **App Service Deployment Issues**:
   - Check application logs in Azure Portal
   - Verify Python version and dependencies
   - Review environment variable configuration

### Support Resources
- [Azure ARM Template Documentation](https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/)
- [Azure Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/)
- [Azure CosmosDB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)