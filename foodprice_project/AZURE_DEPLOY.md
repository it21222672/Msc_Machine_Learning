# Host the model on Microsoft Azure (step by step)

You will run **one script**. Azure builds the Docker image for you (you do NOT need Docker on your PC).

## What you need
1. An Azure account with an active subscription (free trial or student credit works: https://azure.microsoft.com/free/students).
2. Azure CLI installed: https://aka.ms/installazurecliwindows (restart PowerShell afterwards).

## Steps (PowerShell)
```powershell
cd C:\InternalTraining\foodprice_project        # the folder that contains Dockerfile
az login                                         # browser opens, sign in
Set-ExecutionPolicy -Scope Process Bypass        # allow the script for this window only
.\azure_deploy.ps1
```
Wait ~5-10 minutes. At the end it prints the link, e.g. `https://foodprice-spike-1234.azurewebsites.net`.
Open it: the Streamlit dashboard (which calls the FastAPI model inside the same container) appears.

## What the script creates
| Azure resource | Purpose |
|---|---|
| Resource group `rg-foodprice` | folder holding everything |
| Container Registry (Basic) | stores the Docker image built from your Dockerfile |
| App Service plan B1 (Linux) | the server |
| Web App | runs the container; `WEBSITES_PORT=7860` tells Azure which port the app uses; WebSockets ON (Streamlit needs them) |

## Cost
B1 is about USD 13/month (billed per hour) plus a few cents for the registry. The Free (F1) plan does not run custom containers. **Delete when your assignment is graded:**
```powershell
az group delete --name rg-foodprice --yes
```

## Update after changing code
```powershell
az acr build --registry <ACR_NAME> --image foodprice:v1 .
az webapp restart --resource-group rg-foodprice --name <APP_NAME>
```

## Troubleshooting
- *Site shows "Application Error" or loads forever:* wait 5 minutes (image pull); then `az webapp log tail --resource-group rg-foodprice --name <APP_NAME>`.
- *"MissingSubscriptionRegistration":* the script registers providers; if it still fails, run `az provider register --namespace Microsoft.Web --wait`.
- *"quota / SKU not available" in a region:* change `$LOC` in the script (e.g. `centralindia`, `eastus`, `westeurope`).
- *Student subscription blocks B1:* try `--sku B2`/`S1`, or use the free alternative Hugging Face Spaces (see README).

## For the report
Architecture: Browser -> Azure App Service (container) -> Streamlit dashboard -> FastAPI `/predict` -> LightGBM model + SHAP. Add a screenshot of the live Azure URL and the Azure portal page of the Web App.
