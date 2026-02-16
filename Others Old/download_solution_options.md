# Power BI Report Download Solutions - PBIP/TMDL Format

## Problem Statement
Power BI REST API **does NOT support** downloading reports in PBIP/TMDL format. It only supports:
- PBIX format (binary file)
- PDF, PPTX, PNG exports

## Current Situation
Your Python `fabric_client.py` works for **Microsoft Fabric workspaces** but NOT for regular Power BI Service.

---

## Solution Options

### ✅ Option 1: C# Console App with Power BI Desktop Automation (RECOMMENDED)

**Approach:** Use Power BI Desktop COM automation to open PBIX and save as PBIP

**Advantages:**
- ✅ Native Microsoft solution
- ✅ Official PBIP/TMDL support
- ✅ No REST API limitations
- ✅ Works with Power BI Service reports

**Implementation:**

```csharp
// C# Console Application
using System;
using System.IO;
using Microsoft.AnalysisServices.Tabular;
using Microsoft.PowerBI.Api;
using Microsoft.Rest;

namespace PowerBIDownloader
{
    class Program
    {
        static async Task Main(string[] args)
        {
            // Step 1: Download PBIX from Power BI REST API
            var pbixPath = await DownloadPBIX(workspaceId, reportId);
            
            // Step 2: Use Power BI Desktop to convert PBIX to PBIP
            var pbipPath = ConvertToProjectFormat(pbixPath);
            
            Console.WriteLine($"Downloaded: {pbipPath}");
        }

        static async Task<string> DownloadPBIX(string workspaceId, string reportId)
        {
            // Use Power BI REST API
            var client = new PowerBIClient(credentials);
            var export = await client.Reports.ExportReportInGroupAsync(workspaceId, reportId);
            
            // Save PBIX file
            var pbixPath = $"temp_{reportId}.pbix";
            File.WriteAllBytes(pbixPath, export);
            return pbixPath;
        }

        static string ConvertToProjectFormat(string pbixPath)
        {
            // Use AMO/TOM library to extract TMDL
            var server = new Server();
            server.Connect($"Provider=MSOLAP;Data Source={pbixPath}");
            
            var database = server.Databases[0];
            var model = database.Model;
            
            // Export as TMDL
            var outputDir = Path.GetDirectoryName(pbixPath) + "\\PBIP";
            Directory.CreateDirectory(outputDir);
            
            // Save model definition
            var tmdl = Microsoft.AnalysisServices.Tabular.TmdlSerializer.SerializeModel(model);
            File.WriteAllText($"{outputDir}\\model.tmdl", tmdl);
            
            return outputDir;
        }
    }
}
```

**Call from Python:**
```python
import subprocess
import json

def download_as_pbip(workspace_id, report_id, output_dir):
    """Download Power BI report as PBIP using C# helper"""
    result = subprocess.run([
        "PowerBIDownloader.exe",
        "--workspace", workspace_id,
        "--report", report_id,
        "--output", output_dir
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        return True, result.stdout
    else:
        return False, result.stderr
```

---

### ✅ Option 2: PowerShell with XMLA Endpoint (For Datasets Only)

**Approach:** Use Analysis Services PowerShell module to extract TMDL from datasets

**Advantages:**
- ✅ Pure PowerShell solution
- ✅ Works with Premium/Fabric workspaces
- ✅ Direct TMDL export

**Limitations:**
- ⚠️ Requires Premium or Fabric capacity
- ⚠️ XMLA endpoint must be enabled
- ⚠️ Only works for datasets, not reports

**Implementation:**

```powershell
# download_tmdl.ps1
param(
    [string]$WorkspaceId,
    [string]$DatasetId,
    [string]$OutputPath,
    [string]$TenantId,
    [string]$ClientId,
    [string]$ClientSecret
)

# Install required modules
if (-not (Get-Module -ListAvailable -Name SqlServer)) {
    Install-Module -Name SqlServer -Force -AllowClobber
}

Import-Module SqlServer

# Authenticate
$securePassword = ConvertTo-SecureString $ClientSecret -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($ClientId, $securePassword)

# Connect to XMLA endpoint
$connectionString = "Provider=MSOLAP;Data Source=powerbi://api.powerbi.com/v1.0/myorg/$WorkspaceId;User ID=app:$ClientId@$TenantId;Password=$ClientSecret;"

try {
    # Connect to Analysis Services
    $server = New-Object Microsoft.AnalysisServices.Tabular.Server
    $server.Connect($connectionString)
    
    # Get database (dataset)
    $database = $server.Databases.FindByName($DatasetId)
    
    if ($null -eq $database) {
        Write-Error "Dataset not found: $DatasetId"
        exit 1
    }
    
    # Export TMDL
    $model = $database.Model
    $tmdlSerializer = New-Object Microsoft.AnalysisServices.Tabular.TmdlSerializer
    
    # Create output directory structure
    $datasetPath = Join-Path $OutputPath "$($database.Name).Dataset"
    $definitionPath = Join-Path $datasetPath "definition"
    New-Item -ItemType Directory -Path $definitionPath -Force | Out-Null
    
    # Serialize model to TMDL format
    $tmdlSerializer.SerializeModelToFolder($model, $definitionPath)
    
    # Create .pbip metadata file
    $pbipContent = @{
        version = "1.0"
        artifacts = @(
            @{
                report = @{
                    path = "$($database.Name).Report"
                    type = "report"
                }
                dataset = @{
                    path = "$($database.Name).Dataset"
                    type = "dataset"
                }
            }
        )
    } | ConvertTo-Json -Depth 10
    
    $pbipFile = Join-Path $OutputPath "$($database.Name).pbip"
    Set-Content -Path $pbipFile -Value $pbipContent
    
    Write-Host "✓ Successfully exported TMDL to: $datasetPath" -ForegroundColor Green
    exit 0
}
catch {
    Write-Error "Failed to export TMDL: $_"
    exit 1
}
finally {
    if ($server) {
        $server.Disconnect()
    }
}
```

**Call from Python:**
```python
def download_dataset_tmdl_via_powershell(workspace_id, dataset_id, output_dir, config):
    """Download dataset as TMDL using PowerShell XMLA endpoint"""
    
    ps_script = r".\download_tmdl.ps1"
    
    cmd = [
        "pwsh.exe", "-ExecutionPolicy", "Bypass",
        "-File", ps_script,
        "-WorkspaceId", workspace_id,
        "-DatasetId", dataset_id,
        "-OutputPath", output_dir,
        "-TenantId", config.tenant_id,
        "-ClientId", config.client_id,
        "-ClientSecret", config.client_secret
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return True, f"Downloaded to {output_dir}"
    else:
        return False, result.stderr
```

---

### ✅ Option 3: Hybrid Approach (Keep Python for Fabric, Add C#/PowerShell for Power BI)

**Best of Both Worlds:**

1. **Keep `fabric_client.py`** for Microsoft Fabric workspaces (already working)
2. **Add C# helper** for Power BI Service reports → PBIP conversion
3. **Add PowerShell XMLA** for Premium datasets → TMDL export

**Architecture:**

```
┌─────────────────────────────────────────┐
│  Python GUI (main_window.py)           │
└─────────────────────────────────────────┘
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
┌─────────┐      ┌──────────────┐
│ Fabric  │      │ Power BI     │
│ Client  │      │ Downloader   │
│ (Python)│      │ (C#/PS)      │
└─────────┘      └──────────────┘
    ↓                   ↓
  Fabric            Power BI
  REST API          REST API
  (PBIP/TMDL)      (PBIX → PBIP)
```

**Implementation:**

```python
# src/services/powerbi_downloader.py
import subprocess
import os
from pathlib import Path
from typing import Tuple

class PowerBIDownloader:
    """
    Download Power BI reports as PBIP/TMDL format
    Uses C# helper or PowerShell XMLA for conversion
    """
    
    def __init__(self, method: str = "csharp"):
        """
        Args:
            method: "csharp" or "powershell-xmla"
        """
        self.method = method
        self.base_dir = Path(__file__).parent.parent.parent
        
    def download_report_as_pbip(
        self, 
        workspace_id: str, 
        report_id: str,
        output_dir: str,
        config: dict
    ) -> Tuple[bool, str]:
        """
        Download Power BI report as PBIP format
        
        Args:
            workspace_id: Power BI workspace GUID
            report_id: Report GUID
            output_dir: Output directory path
            config: Auth config (tenant_id, client_id, client_secret)
        """
        
        if self.method == "csharp":
            return self._download_via_csharp(workspace_id, report_id, output_dir, config)
        elif self.method == "powershell-xmla":
            return self._download_via_xmla(workspace_id, report_id, output_dir, config)
        else:
            return False, f"Unknown method: {self.method}"
    
    def _download_via_csharp(self, workspace_id, report_id, output_dir, config):
        """Download using C# helper executable"""
        
        exe_path = self.base_dir / "tools" / "PowerBIDownloader.exe"
        
        if not exe_path.exists():
            return False, f"C# helper not found: {exe_path}"
        
        cmd = [
            str(exe_path),
            "--workspace", workspace_id,
            "--report", report_id,
            "--output", output_dir,
            "--tenant", config["tenant_id"],
            "--clientid", config["client_id"],
            "--clientsecret", config["client_secret"]
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                return True, f"Downloaded to {output_dir}"
            else:
                return False, f"Download failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Download timed out after 5 minutes"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _download_via_xmla(self, workspace_id, dataset_id, output_dir, config):
        """Download using PowerShell XMLA endpoint"""
        
        ps_script = self.base_dir / "scripts" / "download_tmdl.ps1"
        
        if not ps_script.exists():
            return False, f"PowerShell script not found: {ps_script}"
        
        cmd = [
            "pwsh.exe", "-ExecutionPolicy", "Bypass",
            "-File", str(ps_script),
            "-WorkspaceId", workspace_id,
            "-DatasetId", dataset_id,
            "-OutputPath", output_dir,
            "-TenantId", config["tenant_id"],
            "-ClientId", config["client_id"],
            "-ClientSecret", config["client_secret"]
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, f"Downloaded to {output_dir}"
            else:
                return False, f"Download failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
```

---

## Recommendation

**Use Option 3 (Hybrid Approach):**

1. **Keep Python for Fabric** - Your current `fabric_client.py` works perfectly for Fabric workspaces
2. **Add C# helper for Power BI** - Best for PBIX → PBIP conversion with full feature support
3. **Optionally add PowerShell XMLA** - For Premium workspace datasets if C# doesn't work

This gives you maximum flexibility and reliability.

---

## Next Steps

1. ✅ Choose which solution to implement
2. ✅ Create C# project for Power BI download helper
3. ✅ Update Python GUI to detect source (Fabric vs Power BI) and use appropriate method
4. ✅ Test with both Fabric and Power BI workspaces

---

## Summary Table

| Method | Format | Source | Pros | Cons |
|--------|--------|--------|------|------|
| **Fabric REST API (Python)** | PBIP/TMDL | Fabric Workspaces | ✅ Fast, Native Python | ❌ Fabric only |
| **C# + Power BI Desktop** | PBIP/TMDL | Power BI Service | ✅ Official, Full support | ⚠️ Requires C# helper |
| **PowerShell XMLA** | TMDL | Premium/Fabric | ✅ Pure PowerShell | ❌ Premium only, Datasets only |
| **Power BI REST API** | PBIX | Power BI Service | ✅ Simple | ❌ PBIX only, not PBIP |
