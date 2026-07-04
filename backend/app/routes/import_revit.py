import json

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.import_service import import_revit_json

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/revit-json")
async def upload_revit_json(file: UploadFile = File(...)):
    payload = await read_revit_json(file)
    return run_import(payload)


@router.post("/projects/{project_id}/revit-json")
async def upload_revit_json_to_project(project_id: str, file: UploadFile = File(...)):
    payload = await read_revit_json(file)
    return run_import(payload, project_id=project_id)


async def read_revit_json(file: UploadFile) -> dict:
    if file.filename and not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Please upload a .json file")

    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="JSON file must be 10 MB or smaller")
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded JSON file is empty")
        payload = json.loads(content.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 JSON") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("project"), dict):
        raise HTTPException(status_code=400, detail="Revit JSON must include a project object")
    if not str(
        payload["project"].get("name")
        or payload["project"].get("project_name")
        or ""
    ).strip():
        raise HTTPException(status_code=400, detail="Project name is required")
    if "rooms" in payload and not isinstance(payload["rooms"], list):
        raise HTTPException(status_code=400, detail="Rooms must be a JSON array")
    return payload


def run_import(payload: dict, project_id: str | None = None):
    try:
        return import_revit_json(payload, project_id=project_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


