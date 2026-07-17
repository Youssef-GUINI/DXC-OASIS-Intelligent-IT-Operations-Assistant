$ROOT="."

# ===========================
# DIRECTORIES
# ===========================

$folders=@(

# Backend
"backend/app/core",
"backend/app/api/v1",
"backend/app/orchestrator",

"backend/app/personas",
"backend/app/personas/linux",
"backend/app/personas/storage",

"backend/app/rag",
"backend/app/rag/linux_kb",
"backend/app/rag/storage_kb",

"backend/app/mcp",
"backend/app/mcp/linux",
"backend/app/mcp/linux/tools",
"backend/app/mcp/storage",
"backend/app/mcp/storage/tools",

"backend/app/models",
"backend/app/schemas",
"backend/app/services",

"backend/app/reports",
"backend/app/reports/templates",

"backend/app/dashboard",

"backend/app/middleware",

"backend/app/database",

"backend/app/utils",

"backend/alembic",
"backend/alembic/versions",

"backend/tests",

# Frontend

"frontend/src",

"frontend/src/routes",

"frontend/src/components",

"frontend/src/components/common",
"frontend/src/components/layout",
"frontend/src/components/charts",

"frontend/src/hooks",

"frontend/src/lib",

"frontend/src/store",

"frontend/src/types",

"frontend/src/services",

"frontend/src/assets",

"frontend/src/workspaces",

"frontend/src/workspaces/linux",
"frontend/src/workspaces/storage",
"frontend/src/workspaces/admin",

"frontend/public",

# Docs

"docs",
"docs/architecture",
"docs/srs",
"docs/uml",
"docs/api",
"docs/database",

# Deployment

".github/workflows"

)

foreach($f in $folders){
    New-Item -ItemType Directory -Force -Path "$ROOT/$f" | Out-Null
}

# ===========================
# FILES
# ===========================

$files=@(

# ---------------- Backend ----------------

"backend/app/main.py",

"backend/app/__init__.py",

"backend/app/core/__init__.py",
"backend/app/core/config.py",
"backend/app/core/security.py",
"backend/app/core/logging.py",

"backend/app/api/__init__.py",
"backend/app/api/deps.py",

"backend/app/api/v1/auth.py",
"backend/app/api/v1/linux.py",
"backend/app/api/v1/storage.py",
"backend/app/api/v1/admin.py",
"backend/app/api/v1/cross_domain.py",
"backend/app/api/v1/dashboard.py",

"backend/app/orchestrator/__init__.py",
"backend/app/orchestrator/orchestrator.py",
"backend/app/orchestrator/llm_router.py",
"backend/app/orchestrator/cross_domain_manager.py",

"backend/app/personas/__init__.py",
"backend/app/personas/base_persona.py",

"backend/app/personas/linux/__init__.py",
"backend/app/personas/linux/agent.py",
"backend/app/personas/linux/prompts.py",

"backend/app/personas/storage/__init__.py",
"backend/app/personas/storage/agent.py",
"backend/app/personas/storage/prompts.py",

"backend/app/rag/__init__.py",
"backend/app/rag/chunking.py",
"backend/app/rag/embeddings.py",
"backend/app/rag/vectorstore.py",
"backend/app/rag/retriever.py",
"backend/app/rag/loader.py",

"backend/app/mcp/__init__.py",

"backend/app/mcp/linux/__init__.py",
"backend/app/mcp/linux/server.py",
"backend/app/mcp/linux/client.py",
"backend/app/mcp/linux/tools/cpu.py",
"backend/app/mcp/linux/tools/ram.py",
"backend/app/mcp/linux/tools/disk.py",
"backend/app/mcp/linux/tools/network.py",
"backend/app/mcp/linux/tools/services.py",

"backend/app/mcp/storage/__init__.py",
"backend/app/mcp/storage/server.py",
"backend/app/mcp/storage/client.py",
"backend/app/mcp/storage/tools/capacity.py",
"backend/app/mcp/storage/tools/backup.py",
"backend/app/mcp/storage/tools/restore.py",
"backend/app/mcp/storage/tools/snapshot.py",
"backend/app/mcp/storage/tools/disaster_recovery.py",

"backend/app/models/__init__.py",
"backend/app/models/user.py",
"backend/app/models/role.py",
"backend/app/models/incident.py",
"backend/app/models/report.py",
"backend/app/models/metric.py",
"backend/app/models/audit_log.py",
"backend/app/models/access_request.py",
"backend/app/models/knowledge_document.py",
"backend/app/models/llm_usage.py",
"backend/app/models/mcp_call.py",

"backend/app/schemas/__init__.py",
"backend/app/schemas/user.py",
"backend/app/schemas/incident.py",
"backend/app/schemas/report.py",
"backend/app/schemas/access_request.py",

"backend/app/services/__init__.py",
"backend/app/services/auth_service.py",
"backend/app/services/incident_service.py",
"backend/app/services/report_service.py",
"backend/app/services/metrics_service.py",
"backend/app/services/audit_service.py",
"backend/app/services/access_request_service.py",

"backend/app/reports/generator.py",

"backend/app/dashboard/kpi_service.py",

"backend/app/middleware/auth_middleware.py",
"backend/app/middleware/rbac_middleware.py",
"backend/app/middleware/audit_middleware.py",

"backend/app/database/base.py",
"backend/app/database/session.py",

"backend/app/utils/helpers.py",

"backend/alembic/env.py",

"backend/tests/test_auth.py",
"backend/tests/test_orchestrator.py",
"backend/tests/test_personas.py",
"backend/tests/test_rag.py",
"backend/tests/test_mcp.py",

"backend/requirements.txt",
"backend/.env.example",
"backend/Dockerfile",
"backend/alembic.ini",

# ---------------- Frontend ----------------

"frontend/src/main.tsx",
"frontend/src/App.tsx",

"frontend/src/routes/index.tsx",

"frontend/src/lib/api.ts",
"frontend/src/lib/auth.ts",

"frontend/src/store/authStore.ts",

"frontend/src/services/linux.ts",
"frontend/src/services/storage.ts",
"frontend/src/services/admin.ts",

"frontend/src/workspaces/linux/Dashboard.tsx",
"frontend/src/workspaces/linux/Chat.tsx",
"frontend/src/workspaces/linux/IncidentHistory.tsx",
"frontend/src/workspaces/linux/Reports.tsx",
"frontend/src/workspaces/linux/KPIs.tsx",

"frontend/src/workspaces/storage/Dashboard.tsx",
"frontend/src/workspaces/storage/Chat.tsx",
"frontend/src/workspaces/storage/IncidentHistory.tsx",
"frontend/src/workspaces/storage/Reports.tsx",
"frontend/src/workspaces/storage/KPIs.tsx",

"frontend/src/workspaces/admin/UserManagement.tsx",
"frontend/src/workspaces/admin/RoleManagement.tsx",
"frontend/src/workspaces/admin/CrossDomainRequests.tsx",
"frontend/src/workspaces/admin/AuditLogs.tsx",
"frontend/src/workspaces/admin/Metrics.tsx",

"frontend/package.json",
"frontend/vite.config.ts",
"frontend/tailwind.config.ts",
"frontend/index.html",
"frontend/Dockerfile",

# ---------------- Root ----------------

"docker-compose.yml",

".gitignore",

"README.md",

".github/workflows/ci.yml"

)

foreach($file in $files){
    New-Item -ItemType File -Force -Path "$ROOT/$file" | Out-Null
}

Write-Host ""
Write-Host "======================================="
Write-Host " OASIS AI Copilot V1 created successfully"
Write-Host "======================================="