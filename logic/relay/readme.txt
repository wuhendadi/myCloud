Box Relay Server

1.Implement relay between client and box, and add test cases.
Run relay server first:
$ python src\relay.py
Run all test cases by:
$ python -m unittest -v tests.test_relay

3.default configuration parameters:
relay ip¡¢hub ip:        127.0.0.1
relay port for box:      8100
relay port for client:   8120
hub port:                8200

REF:
1.Hub api for box relay server.
svn://192.168.0.8/CherryCL/trunk/¿ª·¢ÎÄµµ/platform/PopoCloud Developer Reference.docx