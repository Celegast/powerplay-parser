"""format_for_excel lists our power against the strongest other power (highest control score wins)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from powerplay_ocr import PowerplayOCR

fmt = PowerplayOCR.format_for_excel


def _info(*powers):
    return {'system_name': 'X', 'powers': [{'name': n, 'score': s, 'rank': r} for n, s, r in powers]}


def test_ours_third_vs_leader():
    info = _info(('Jerome Archer', 120702, 1), ('Li Yong-Rui', 412, 2), ('Pranav Antal', 262, None))
    assert fmt(None, info) == 'X\tPranav Antal\tJerome Archer\t\t120702\t262\t'


def test_ours_first_vs_runner_up():
    info = _info(('Pranav Antal', 54306, 1), ('Li Yong-Rui', 111, 2))
    assert fmt(None, info) == 'X\tPranav Antal\tLi Yong-Rui\t\t111\t54306\t'


def test_ours_zero_score_kept():
    info = _info(('Li Yong-Rui', 2447, 1), ('Pranav Antal', 0, 2))
    assert fmt(None, info) == 'X\tPranav Antal\tLi Yong-Rui\t\t2447\t0\t'


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok ', name)
