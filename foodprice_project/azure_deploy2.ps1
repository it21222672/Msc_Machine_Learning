# Deploy to Azure App Service. Finds a region your subscription allows (Azure for Students limits regions).
# Run in PowerShell from the folder that contains the Dockerfile, after:  az login
$suffix = Get-Random -Minimum 1000 -Maximum 9999
$RG   = "rg-foodprice"
$ACR  = "foodpriceacr$suffix"
$PLAN = "plan-foodprice"
$APP  = "foodprice-spike-$suffix"
$IMG  = "foodprice:v1"

# 1. Regions to try: first the ones your subscription's policy allows, then common student regions
$candidates = @()
try {
  $allowed = az policy assignment list --query "[].parameters.listOfAllowedLocations.value[]" -o tsv 2>$null
  if ($allowed) { $candidates += ($allowed -split "`r?`n" | Where-Object { $_ -and $_ -ne "global" }) }
} catch {}
$candidates += "centralindia","uaenorth","koreacentral","polandcentral","italynorth","spaincentral","austriaeast","malaysiawest","indonesiacentral","southindia","japaneast","eastasia","westeurope","northeurope","swedencentral","eastus2","westus3"
$candidates = $candidates | Select-Object -Unique

az group create --name $RG --location centralindia 2>$null | Out-Null
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.Web --wait

$LOC = $null
foreach ($r in $candidates) {
  Write-Host "Trying region: $r" -ForegroundColor Cyan
  az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true --location $r 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { continue }
  az appservice plan create --name $PLAN --resource-group $RG --is-linux --sku B1 --location $r 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $LOC = $r; break }
  Write-Host "  plan not allowed in $r, removing registry and trying next" -ForegroundColor Yellow
  az acr delete --name $ACR --resource-group $RG --yes 2>$null | Out-Null
}
if (-not $LOC) { Write-Host "No allowed region found. Send a screenshot of this window to your helper." -ForegroundColor Red; exit 1 }
Write-Host "Using region: $LOC" -ForegroundColor Green

# 2. Build image in Azure
az acr build --registry $ACR --image $IMG .
if ($LASTEXITCODE -ne 0) { Write-Host "Image build failed. Send a screenshot of the error." -ForegroundColor Red; exit 1 }

# 3. Create the web app
$pw = az acr credential show --name $ACR --query "passwords[0].value" -o tsv
az webapp create --resource-group $RG --plan $PLAN --name $APP `
    --container-image-name "$ACR.azurecr.io/$IMG" `
    --container-registry-url "https://$ACR.azurecr.io" `
    --container-registry-user $ACR `
    --container-registry-password $pw
az webapp config appsettings set --resource-group $RG --name $APP --settings WEBSITES_PORT=7860 PORT=7860
az webapp config set --resource-group $RG --name $APP --web-sockets-enabled true
az webapp restart --resource-group $RG --name $APP

Write-Host ""
Write-Host "Done. Open: https://$APP.azurewebsites.net  (first start can take 2-5 minutes)" -ForegroundColor Green
Write-Host "To stop paying later, delete everything with:  az group delete --name $RG --yes"
