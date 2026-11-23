<#
.SYNOPSIS
Creates the backend Container App with scale to zero and HTTP health probes.

.DESCRIPTION
Health probes can only be set through a YAML definition, so this script builds one.
The API key is asked as hidden input, stored as a Container Apps secret, and exists on
disk only in a temporary file that is removed when the script ends. JSON is valid YAML,
so the definition is written as JSON to avoid quoting problems.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $ResourceGroup,
    [Parameter(Mandatory)] [string] $EnvironmentName,
    [Parameter(Mandatory)] [string] $AppName,
    [Parameter(Mandatory)] [string] $Image,
    [Parameter(Mandatory)] [string] $FrontendOrigin,
    [string] $OpenAiModel = "gpt-6-luna",
    [Parameter(Mandatory)] [securestring] $OpenAiApiKey
)

$ErrorActionPreference = "Stop"

function Read-AzValue {
    param([string] $Query)
    $value = az containerapp env show --name $EnvironmentName --resource-group $ResourceGroup --query $Query --output tsv
    if ($LASTEXITCODE -ne 0 -or -not $value) {
        throw "Could not read '$Query' from environment '$EnvironmentName'."
    }
    return $value
}

function New-HttpProbe {
    param([string] $Type, [int] $Period, [int] $Timeout, [int] $Failures)
    return @{
        type             = $Type
        httpGet          = @{ path = "/api/health"; port = 8000 }
        periodSeconds    = $Period
        timeoutSeconds   = $Timeout
        failureThreshold = $Failures
    }
}

$apiKey = (New-Object System.Net.NetworkCredential("", $OpenAiApiKey)).Password
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    throw "The API key is empty."
}

$definition = @{
    location   = Read-AzValue "location"
    properties = @{
        environmentId = Read-AzValue "id"
        configuration = @{
            activeRevisionsMode = "Single"
            ingress             = @{
                external      = $true
                targetPort    = 8000
                transport     = "auto"
                allowInsecure = $false
            }
            secrets             = @(@{ name = "openai-api-key"; value = $apiKey })
        }
        template      = @{
            containers = @(
                @{
                    name      = "backend"
                    image     = $Image
                    resources = @{ cpu = 0.25; memory = "0.5Gi" }
                    env       = @(
                        @{ name = "LLM_PROVIDER"; value = "openai" }
                        @{ name = "OPENAI_API_KEY"; secretRef = "openai-api-key" }
                        @{ name = "OPENAI_MODEL"; value = $OpenAiModel }
                        @{ name = "LLM_TEMPERATURE"; value = "none" }
                        @{ name = "LLM_TIMEOUT_SECONDS"; value = "20" }
                        @{ name = "APP_ENV"; value = "production" }
                        @{ name = "FRONTEND_ORIGIN"; value = $FrontendOrigin }
                        @{ name = "RATE_LIMIT_PER_MINUTE"; value = "20" }
                        @{ name = "TRUST_PROXY_HEADERS"; value = "true" }
                    )
                    probes    = @(
                        (New-HttpProbe -Type "Startup" -Period 2 -Timeout 2 -Failures 30)
                        (New-HttpProbe -Type "Readiness" -Period 10 -Timeout 3 -Failures 3)
                        (New-HttpProbe -Type "Liveness" -Period 30 -Timeout 3 -Failures 3)
                    )
                }
            )
            scale      = @{ minReplicas = 0; maxReplicas = 1 }
        }
    }
}

$definitionPath = [System.IO.Path]::GetTempFileName()
try {
    $json = $definition | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($definitionPath, $json, (New-Object System.Text.UTF8Encoding($false)))

    $hostName = az containerapp create `
        --name $AppName `
        --resource-group $ResourceGroup `
        --yaml $definitionPath `
        --query "properties.configuration.ingress.fqdn" `
        --output tsv
    if ($LASTEXITCODE -ne 0) {
        throw "Creating the Container App failed."
    }
    Write-Output "Backend URL: https://$hostName"
}
finally {
    Remove-Item -LiteralPath $definitionPath -Force -ErrorAction SilentlyContinue
}
