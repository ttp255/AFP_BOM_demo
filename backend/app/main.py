from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import bom, catalog, exports, import_revit, projects, search, suggestions

app = FastAPI(title="AFP Paint Suggestion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_revit.router, prefix="/api/import", tags=["Import"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(bom.router, prefix="/api/bom", tags=["BOM"])
app.include_router(suggestions.router, prefix="/api/suggestions", tags=["Suggestions"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(catalog.router, prefix="/api/catalog", tags=["Catalog"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])


@app.get("/health")
def health():
    return {"status": "ok"}
