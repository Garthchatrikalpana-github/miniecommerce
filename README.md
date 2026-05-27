# miniecommerce
python3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Azure Container Apps is actually the best fit here — better than App Service for a containerized FastAPI app, and far simpler than AKS. You get auto-scaling, built-in HTTPS, and a public URL out of the box. Let me give you the full guide + IAD diagram.
  ::view-transition-group(*),
  ::view-transition-old(*),
  ::view-transition-new(*) {
    animation-duration: 0.25s;
    animation-timing-function: cubic-bezier(0.19, 1, 0.22, 1);
  }
VvisualizeVvisualize show_widget
Why Azure Container Apps (not Function App)
Function App is for short event-triggered tasks (a webhook, a cron job, a queue processor). Your app is a long-running web server with routes, sessions, and a DB connection pool — Function App is the wrong shape. Container Apps is the right one: it runs your full FastAPI app exactly like you'd run it locally, just managed by Azure.

All Azure resources you're using
ResourceNameWhat it doesResource Grouprg-minicommerce-prodLogical container for all resourcesContainer RegistryacrminicommerceprodStores your Docker imageContainer Apps Environmentcae-minicommerceNetworking/logging sandbox for your appContainer Appca-minicommerce-apiRuns your FastAPI container, gives you the public URLManaged Identityid-minicommerceLets your app pull secrets without passwordsKey Vaultkv-minicommerceStores DATABASE_URL, SECRET_KEY, SESSION_SECRET securelyPostgreSQL Flexible Serverpsql-minicommerce-prodYour managed Postgres DBLog Analytics Workspacelog-minicommerceCollects logs from your app (replaces app.log)

Extra files you need to create
1. Dockerfile (required — doesn't exist in your project)
dockerfileFROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
2. .dockerignore (keeps image lean)
.venv/
__pycache__/
*.pyc
.env
app.log
*.zip
3. Fix requirements.txt — fastapi is missing
Add this line (your app imports it but it's not listed):
fastapi>=0.115.0

Full setup steps
Step 1 — Install tools & login
bashaz login
az extension add --name containerapp --upgrade
Step 2 — Create resource group
bashaz group create \
  --name rg-minicommerce-prod \
  --location eastus
Step 3 — Create Container Registry & push image
bash# Create registry
az acr create \
  --resource-group rg-minicommerce-prod \
  --name acrminicommerceprod \
  --sku Basic \
  --admin-enabled true

# Build & push image (run from your project folder)
az acr build \
  --registry acrminicommerceprod \
  --image minicommerce:latest .
No local Docker needed — az acr build builds in the cloud.
Step 4 — Create PostgreSQL
bashaz postgres flexible-server create \
  --resource-group rg-minicommerce-prod \
  --name psql-minicommerce-prod \
  --admin-user pgadmin \
  --admin-password "<YourStrongPassword>" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16

az postgres flexible-server db create \
  --resource-group rg-minicommerce-prod \
  --server-name psql-minicommerce-prod \
  --database-name minicommerce
Your connection string will be:
postgresql://pgadmin:<password>@psql-minicommerce-prod.postgres.database.azure.com:5432/minicommerce
Step 5 — Create Key Vault & store secrets
bashaz keyvault create \
  --name kv-minicommerce \
  --resource-group rg-minicommerce-prod \
  --location eastus

az keyvault secret set --vault-name kv-minicommerce \
  --name DATABASE-URL \
  --value "postgresql://pgadmin:<password>@psql-minicommerce-prod.postgres.database.azure.com:5432/minicommerce"

az keyvault secret set --vault-name kv-minicommerce \
  --name SECRET-KEY --value "<generate-a-random-string>"

az keyvault secret set --vault-name kv-minicommerce \
  --name SESSION-SECRET --value "<generate-a-random-string>"
Step 6 — Create Log Analytics workspace
bashaz monitor log-analytics workspace create \
  --resource-group rg-minicommerce-prod \
  --workspace-name log-minicommerce
Step 7 — Create Container Apps Environment
bashLOG_WS_ID=$(az monitor log-analytics workspace show \
  --resource-group rg-minicommerce-prod \
  --workspace-name log-minicommerce \
  --query customerId -o tsv)

LOG_WS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group rg-minicommerce-prod \
  --workspace-name log-minicommerce \
  --query primarySharedKey -o tsv)

az containerapp env create \
  --name cae-minicommerce \
  --resource-group rg-minicommerce-prod \
  --location eastus \
  --logs-workspace-id $LOG_WS_ID \
  --logs-workspace-key $LOG_WS_KEY
Step 8 — Deploy the Container App
bashaz containerapp create \
  --name ca-minicommerce-api \
  --resource-group rg-minicommerce-prod \
  --environment cae-minicommerce \
  --image acrminicommerceprod.azurecr.io/minicommerce:latest \
  --registry-server acrminicommerceprod.azurecr.io \
  --registry-username acrminicommerceprod \
  --registry-password $(az acr credential show --name acrminicommerceprod --query passwords[0].value -o tsv) \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 3 \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    SECRET_KEY=secretref:secret-key \
    SESSION_SECRET=secretref:session-secret \
  --secrets \
    "database-url=$(az keyvault secret show --vault-name kv-minicommerce --name DATABASE-URL --query value -o tsv)" \
    "secret-key=$(az keyvault secret show --vault-name kv-minicommerce --name SECRET-KEY --query value -o tsv)" \
    "session-secret=$(az keyvault secret show --vault-name kv-minicommerce --name SESSION-SECRET --query value -o tsv)"
Step 9 — Allow Container App to reach PostgreSQL
bash# Get the outbound IP of your container app environment
OUTBOUND_IP=$(az containerapp env show \
  --name cae-minicommerce \
  --resource-group rg-minicommerce-prod \
  --query properties.staticIp -o tsv)

az postgres flexible-server firewall-rule create \
  --resource-group rg-minicommerce-prod \
  --name psql-minicommerce-prod \
  --rule-name allow-containerapp \
  --start-ip-address $OUTBOUND_IP \
  --end-ip-address $OUTBOUND_IP

How the end user accesses it
After step 8, run:
bashaz containerapp show \
  --name ca-minicommerce-api \
  --resource-group rg-minicommerce-prod \
  --query properties.configuration.ingress.fqdn \
  --output tsv
You'll get a URL like:
ca-minicommerce-api.happyforest-abc123.eastus.azurecontainerapps.io
That's your live public HTTPS URL — no extra config needed. Share it and it works.

Cost estimate
ResourceTier~MonthlyContainer AppConsumption (pay-per-use)~$0–5 (scales to 0 when idle)PostgreSQLStandard_B1ms Burstable~$12Container RegistryBasic~$5Key VaultStandard~$1Log AnalyticsPay-per-GB~$2Total~$20–25/month

TL;DR of what to create: Dockerfile + .dockerignore + add fastapi to requirements. Everything else (env vars, secrets, URLs) is handled by Azure through the CLI commands above. Want me to generate a single shell script that runs all of this end to end?
