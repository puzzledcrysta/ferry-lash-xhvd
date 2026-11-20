import json
from datetime import datetime, timezone
from time import perf_counter
from app.manifest import manifest
from app.pipeline import execute
from app.store import connection
from app.modules.quality.resolutions import apply_view, latest
from .repository import fetch, persist, lookup


def run(source,book):
    proof = manifest(source,book)
    started = perf_counter()
    result = execute(source,book)
    created = datetime.now(timezone.utc).isoformat()
    proof.update(elapsed_ms=round((perf_counter()-started)*1000,2),created=created)
    result['manifest'] = proof
    persist(proof['run_id'],source,book,result,created)
    return get(proof['run_id'])


def replay(run_id):
    old = fetch(run_id)
    return run(old['source'],old['book'])


def get(run_id):
    with connection() as db:
        record = lookup(db,run_id)
        result = json.loads(record['result'])
        book = record['book']
        resolutions = latest(db,run_id)
    return apply_view(result,book,resolutions)
