"""--debug-pause correction prompt: typed numbers replace flagged values in the capture files, Enter keeps them."""
import builtins
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from auto_capture import confirm_flagged_values
from powerplay_ocr import PowerplayOCR


class _Ocr:
    format_for_excel = PowerplayOCR.format_for_excel   # doesn't touch self; skips Tesseract setup


def _std(um, rf):
    return {'system_name': '', 'controlling_power': 'Pranav Antal', 'opposing_power': '',
            'system_status': 'FORTIFIED', 'undermining_points': um, 'reinforcing_points': rf,
            'initial_control_points': -1}


def test_correct_and_keep():
    systems = {'Sol': _std(100, 5000), 'Lave': _std(10, 90000)}
    ocr = _Ocr()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'capture.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('header\n')
            for name, info in systems.items():
                f.write(ocr.format_for_excel(info, original_system_name=name) + '\n')
        sol_line = open(path, encoding='utf-8').read().splitlines()[1]

        answers = iter(['abc', '9.123', ''])   # Lave: invalid, then 9.123 -> 9123; Sol: Enter keeps 100
        real_input, builtins.input = builtins.input, lambda prompt='': next(answers)
        try:
            confirm_flagged_values([('Lave', 'Reinforcing', 9000), ('Sol', 'Undermining', 200)],
                                   systems, ocr, [path])
        finally:
            builtins.input = real_input

        lines = open(path, encoding='utf-8').read().splitlines()
    assert lines == ['header', sol_line, 'Lave\tPranav Antal\tFORTIFIED\t\t10\t9123\t'], lines
    assert systems['Lave']['reinforcing_points'] == 9123 and systems['Sol']['undermining_points'] == 100


if __name__ == '__main__':
    test_correct_and_keep()
    print('ok  test_correct_and_keep')
