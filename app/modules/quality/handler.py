from fastapi import APIRouter
from app.inputs import Source, Resolution
from app.modules.intake.service import intake
from app.modules.contract.service import normalize
from app.modules.runs.service import get
from .service import inspect
from .resolutions import resolve

router = APIRouter()

@router.post('/api/quality')
def quality(source: Source):
    return inspect(*normalize(intake(source.raw())))

@router.post('/api/quality/resolve/{run_id}')
def resolve_conflict(run_id: str, resolution: Resolution):
    resolve(run_id,resolution.key,resolution.version,resolution.picks,resolution.note)
    return get(run_id)
