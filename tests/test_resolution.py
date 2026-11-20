import pytest
from decimal import Decimal

MERGE = {'首轴距中线': 33, '轴载序列': 34, '局部限载': 33, '总矩上限': 33}
WHOLE_B = {'首轴距中线': 34, '轴载序列': 34, '局部限载': 34, '总矩上限': 34}
FAILING = {'首轴距中线': 33, '轴载序列': 33, '局部限载': 33, '总矩上限': 34}
NOTE = '甲方补轴载、乙方补轴距，按字段分别采信'


@pytest.fixture
def anchor(client):
    return client.post('/api/runs', json={}).json()['manifest']['run_id']


def resolve(client, anchor, picks=MERGE, version=0, note=NOTE, key='00899'):
    return client.post(f'/api/quality/resolve/{anchor}',
                       json={'key': key, 'version': version, 'picks': picks, 'note': note})


def adopted(view, key='00899'):
    return next((row for row in view['accepted'] if row['key'] == key), None)


def test_stage_lists_disputed_fields(client):
    group, = client.post('/api/quality', json={}).json()['conflicts']
    assert group['key'] == '00899' and group['released'] is False
    assert group['disputed'] == ['首轴距中线', '轴载序列', '局部限载', '总矩上限']
    assert [row['line'] for row in group['candidates']] == [33, 34]


def test_merge_releases_vehicle(client, anchor):
    view = resolve(client, anchor).json()
    row = adopted(view)
    assert row['amount'] == '16' and row['line'] == 33
    assert row['adopted']['picks'] == MERGE and row['adopted']['sources'] == [33, 34]
    assert [item['code'] for item in view['quarantine'] if item['key'] == '00899'] == []
    unadopted, = [item for item in view['suppressed'] if item['key'] == '00899']
    assert (unadopted['line'], unadopted['code']) == (34, 'NOT_ADOPTED')
    assert '轴载序列' in unadopted['detail']
    assert view['counts'] == {'input': 36, 'accepted': 27, 'rejected': 4,
                              'suppressed': 3, 'blank': 1, 'repeated_header': 1}
    assert view['balanced'] is True
    group, = view['conflicts']
    assert group['released'] is True and group['adopted']['version'] == 1
    assert view['resolutions'][0]['picks'] == MERGE


def test_reconcile_counts_adopted(client, anchor):
    view = resolve(client, anchor).json()
    row, = [item for item in view['book']['rows'] if item['key'] == '00899']
    assert (row['code'], row['amount'], row['reference']) == ('MISSING_BOOK', '16', None)
    assert view['book']['mismatched'] == 4 and Decimal(view['book']['delta']) == Decimal('19')


def test_workbench_and_export_share_conclusion(client, anchor):
    view = resolve(client, anchor).json()
    assert client.get(f'/api/runs/{anchor}').json() == view
    proof = client.get(f'/api/export/{anchor}').json()
    assert next(row for row in proof['results'] if row['key'] == '00899')['amount'] == '16'
    assert proof['counts'] == view['counts']
    assert proof['resolutions'][0]['picks'] == MERGE
    assert [item['key'] for item in proof['quarantine']].count('00899') == 0
    row, = [item for item in proof['reconciliation']['rows'] if item['key'] == '00899']
    assert row['code'] == 'MISSING_BOOK'
    assert any(item['code'] == 'NOT_ADOPTED' for item in proof['suppressed'])


def test_partial_picks_cannot_release(client, anchor):
    partial = dict(MERGE)
    del partial['总矩上限']
    response = resolve(client, anchor, picks=partial)
    assert (response.status_code, response.json()['code']) == (422, 'RESOLUTION_PICKS')
    view = client.get(f'/api/runs/{anchor}').json()
    assert adopted(view) is None and view['resolutions'] == []
    assert len([item for item in view['quarantine'] if item['key'] == '00899']) == 2


def test_unknown_source_line(client, anchor):
    response = resolve(client, anchor, picks=dict(MERGE, 总矩上限=999))
    assert (response.status_code, response.json()['code']) == (422, 'RESOLUTION_SOURCE')


def test_note_required(client, anchor):
    response = resolve(client, anchor, note='  ')
    assert (response.status_code, response.json()['code']) == (422, 'RESOLUTION_NOTE')


def test_unknown_conflict(client, anchor):
    response = resolve(client, anchor, key='00101')
    assert (response.status_code, response.json()['code']) == (404, 'CONFLICT_UNKNOWN')
    missing = client.post('/api/quality/resolve/not-found',
                          json={'key': '00899', 'version': 0, 'picks': MERGE, 'note': NOTE})
    assert (missing.status_code, missing.json()['code']) == (404, 'RUN_UNKNOWN')


def test_uncomputable_pick_keeps_quarantine(client, anchor):
    response = resolve(client, anchor, picks=FAILING)
    assert (response.status_code, response.json()['code']) == (422, 'BUSINESS')
    view = client.get(f'/api/runs/{anchor}').json()
    assert adopted(view) is None and view['conflicts'][0]['released'] is False
    assert len([item for item in view['quarantine'] if item['key'] == '00899']) == 2


def test_failed_switch_keeps_old_version(client, anchor):
    assert resolve(client, anchor).status_code == 200
    failed = resolve(client, anchor, picks=FAILING, version=1)
    assert (failed.status_code, failed.json()['code']) == (422, 'BUSINESS')
    view = client.get(f'/api/runs/{anchor}').json()
    assert adopted(view)['amount'] == '16' and view['resolutions'][0]['version'] == 1


def test_switch_resolution(client, anchor):
    assert resolve(client, anchor).status_code == 200
    stale = resolve(client, anchor, picks=WHOLE_B, version=0)
    assert (stale.status_code, stale.json()['code']) == (409, 'STALE')
    view = resolve(client, anchor, picks=WHOLE_B, version=1, note='改按甲方整张采信').json()
    row = adopted(view)
    assert (row['amount'], row['line']) == ('0', 34)
    assert view['resolutions'][0]['version'] == 2
    unadopted, = [item for item in view['suppressed'] if item['key'] == '00899']
    assert unadopted['line'] == 33
    assert view['counts']['input'] == sum(value for key, value in view['counts'].items() if key != 'input')


def test_replay_conserves_records(client, anchor):
    first = resolve(client, anchor).json()
    replayed = client.post(f'/api/runs/{anchor}/replay').json()
    assert replayed == first
    assert len(client.get('/api/runs').json()) == 1
    again = client.post('/api/runs', json={}).json()
    assert again['manifest']['run_id'] == anchor and adopted(again)['amount'] == '16'
    assert len(client.get('/api/runs').json()) == 1


def test_review_and_export_after_resolution(client, anchor):
    resolve(client, anchor)
    review = client.post(f'/api/review/{anchor}',
                         json={'version': 0, 'decision': '确认', 'note': '采信后逐条核对'})
    assert review.status_code == 200
    proof = client.get(f'/api/export/{anchor}').json()
    assert proof['review'][0]['decision'] == '确认'
    assert proof['resolutions'][0]['key'] == '00899'
