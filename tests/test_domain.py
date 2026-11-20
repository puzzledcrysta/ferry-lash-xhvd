from decimal import Decimal
import pytest
from app.errors import DataError
from app.modules.domain.rule import evaluate


def test_opposing(cases):
    # TRAP-10
    actual, evidence = evaluate(cases['opposing'])
    assert actual == Decimal('6')
    assert evidence[:2] == [('负侧弯矩',Decimal('-10'),'吨米'),('正侧弯矩',Decimal('16'),'吨米')]
    exact = dict(cases['opposing'],首轴距中线='-0.1',轴距='0.1',轴载序列='0.1;0.2;0.4')
    assert evaluate(exact)[0] == Decimal('0.03')


def test_balanced(cases):
    actual, evidence = evaluate(cases['balanced'])
    assert actual == Decimal('0')


def test_boundary(cases):
    actual, evidence = evaluate(cases['boundary'])
    assert actual == Decimal('11')


def test_negative(cases):
    actual, evidence = evaluate(cases['negative'])
    assert actual == Decimal('18')


def test_overaxle(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['overaxle'])
    assert error.value.code in {'BUSINESS','NUMBER','RANGE','TIMESTAMP'}


def test_overmoment(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['overmoment'])
    assert error.value.code in {'BUSINESS','NUMBER','RANGE','TIMESTAMP'}


def test_lash(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['lash'])
    assert error.value.code in {'BUSINESS','NUMBER','RANGE','TIMESTAMP'}

