# Deploys the app to Azure App Service WITHOUT Docker/ACR (works on Azure for Students).
# Run from the project folder in PowerShell after:  az login
$RG   = "rg-foodprice"
$PLAN = "plan-foodprice"
$APP  = "foodprice-spike-" + (Get-Random -Minimum 1000 -Maximum 9999)

# 0. Remove leftover registries from the earlier attempts (they cost money and are not needed)
foreach ($n in (az acr list --resource-group $RG --query "[].name" -o tsv 2>$null)) {
  if ($n) { az acr delete --name $n --resource-group $RG --yes 2>$null | Out-Null }
}

# 1. Make sure an App Service plan exists (use the region your subscription allows)
az provider register --namespace Microsoft.Web --wait
$loc = az appservice plan show --name $PLAN --resource-group $RG --query location -o tsv 2>$null
if (-not $loc) {
  $candidates = @("uaenorth","centralindia","koreacentral","polandcentral","italynorth","spaincentral","austriaeast","malaysiawest","indonesiacentral","southindia","japaneast","westeurope","northeurope","swedencentral","eastus2","westus3")
  foreach ($r in $candidates) {
    Write-Host "Trying region: $r" -ForegroundColor Cyan
    az appservice plan create --name $PLAN --resource-group $RG --is-linux --sku B1 --location $r 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $loc = $r; break }
  }
}
if (-not $loc) { Write-Host "No allowed region found." -ForegroundColor Red; exit 1 }
Write-Host "Using region: $loc" -ForegroundColor Green

# 2. Zip the app (only what is needed)
$stage = Join-Path $env:TEMP "foodprice_stage"
$zip   = Join-Path $env:TEMP "foodprice_app.zip"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
if (Test-Path $zip)   { Remove-Item $zip -Force }
robocopy . $stage /E /XD venv notebooks report _dev .git __pycache__ /XF *.zip *.ps1 Dockerfile render.yaml /NFL /NDL /NJH /NJS | Out-Null
tar.exe -a -c -f $zip -C $stage .
Write-Host ("Zip size: {0:N1} MB" -f ((Get-Item $zip).Length/1MB))

# 3. Create the web app (Python 3.11) and configure it
az webapp create --resource-group $RG --plan $PLAN --name $APP --runtime "PYTHON:3.11"
if ($LASTEXITCODE -ne 0) { Write-Host "Web app creation failed. Send a screenshot." -ForegroundColor Red; exit 1 }
az webapp config appsettings set --resource-group $RG --name $APP --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true WEBSITES_PORT=8000 PORT=8000 WEBSITES_CONTAINER_START_TIME_LIMIT=1800 | Out-Null
az webapp config set --resource-group $RG --name $APP --web-sockets-enabled true --startup-file "sh start.sh" | Out-Null

# 4. Upload and build (installs the packages on Azure, takes several minutes)
az webapp deploy --resource-group $RG --name $APP --src-path $zip --type zip

Write-Host ""
Write-Host "Done. Open: https://$APP.azurewebsites.net  (the first start can take 5-10 minutes while packages install)" -ForegroundColor Green
Write-Host "Watch progress with:  az webapp log tail --resource-group $RG --name $APP"
Write-Host "To stop paying later:  az group delete --name $RG --yes"
