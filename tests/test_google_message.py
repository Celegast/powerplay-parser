"""Checks that update_google_sheet surfaces Google's real error text instead of HTML noise."""
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import update_google_sheet as u


def _resp(body, status=200, ctype='text/html; charset=utf-8'):
    r = requests.models.Response()
    r.status_code, r._content, r.encoding = status, body.encode('utf-8'), 'utf-8'
    r.headers['content-type'] = ctype
    return r


# Trimmed copy of the real 405/404 page the deployment returns (German account locale):
# a large ppConfig <script> blob first, then the actual message.
DRIVE_PAGE = ("<!DOCTYPE html><html lang=\"de\"><head><script nonce=\"x\">window['ppConfig'] = {productName: 'x'};"
              + "var a=1;" * 200 + "</script><title>Seite nicht gefunden</title><style>body{margin:0}</style></head>"
              "<body><div>Drive</div><p>Datei kann derzeit nicht geöffnet werden.</p>"
              "<p>Überprüfen Sie die Adresse und versuchen Sie es erneut.</p></body></html>")

# Apps Script's page for an exception thrown by doGet/doPost (quota errors look the same).
SCRIPT_ERROR_PAGE = ("<!DOCTYPE html><html><head><title>Error</title><style>.errorMessage{font-weight:bold}</style>"
                     "</head><body style=\"margin:20px\"><div><img alt=\"Google Apps Script\" src=\"logo.png\"></div>"
                     "<div style=\"text-align:center;font-family:monospace;margin:50px auto 0;max-width:600px\">"
                     "Exception: There are too many scripts running simultaneously for this Google user account."
                     " (line 12, file &quot;Code&quot;)</div></body></html>")


def test_drive_error_page():
    msg = u._google_message(_resp(DRIVE_PAGE, 405))
    assert msg.startswith('Seite nicht gefunden: Drive Datei kann derzeit nicht geöffnet werden.'), msg
    assert 'ppConfig' not in msg and 'var a' not in msg


def test_script_exception_page():
    msg = u._google_message(_resp(SCRIPT_ERROR_PAGE))
    assert msg == ('Error: Exception: There are too many scripts running simultaneously for this Google '
                   'user account. (line 12, file "Code")'), msg


def test_json_error_field():
    assert u._google_message(_resp('{"error":"Sheet not found: X"}', ctype='application/json')) == 'Sheet not found: X'


def test_empty_and_truncation():
    assert u._google_message(_resp('')) == '(empty response)'
    assert len(u._google_message(_resp('<p>' + 'x' * 1000 + '</p>'))) == 300


def test_bounced_echo_is_transient():
    ok = _resp('{"updated":10}', ctype='application/json')
    ok.history = [_resp('', 302)]                                   # /exec → echo
    bounced = _resp('{"error":"Unauthorized"}', ctype='application/json')
    bounced.history = [_resp('', 302), _resp('', 302), _resp('', 302)]  # /exec → echo → /exec → echo
    assert not u._is_transient_failure(ok)
    assert u._is_transient_failure(bounced)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
