import 'dart:io';
import 'dart:convert';
import 'dart:async';

Future<void> main() async {
  var server = await HttpServer.bind('127.0.0.1', 8080);
  print('====================================================');
  print(' ODOO PROXY RUNNING ON http://127.0.0.1:8080');
  print(' USE THIS URL IN THE FLUTTER APP LOGIN SCREEN');
  print('====================================================');

  await for (var request in server) {
    handleRequest(request);
  }
}

void handleRequest(HttpRequest request) async {
  if (request.method == 'OPTIONS') {
    request.response
      ..headers.add('Access-Control-Allow-Origin', '*')
      ..headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
      ..headers.add('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Cookie, X-Openerp-Session-Id')
      ..statusCode = HttpStatus.ok;
    await request.response.close();
    return;
  }

  try {
    var targetUrl = Uri.parse('https://demo1.havano.pro${request.uri.path}');
    var client = HttpClient();
    var proxyRequest = await client.openUrl(request.method, targetUrl);

    // Forward headers, convert X-Openerp-Session-Id to Cookie
    request.headers.forEach((name, values) {
      if (name != 'host' && name != 'origin' && name != 'referer') {
        if (name.toLowerCase() == 'x-openerp-session-id') {
          proxyRequest.headers.add('Cookie', 'session_id=${values.first}');
        } else {
          for (var value in values) {
            proxyRequest.headers.add(name, value);
          }
        }
      }
    });

    // Forward body
    await proxyRequest.addStream(request);
    var proxyResponse = await proxyRequest.close();

    // Read the response body
    var responseBodyBytes = await proxyResponse.expand((b) => b).toList();
    var responseString = utf8.decode(responseBodyBytes, allowMalformed: true);

    // Extract session_id from Set-Cookie and inject it into the JSON result
    String? sessionId;
    proxyResponse.headers.forEach((name, values) {
      if (name.toLowerCase() == 'set-cookie') {
        for (var value in values) {
          var match = RegExp(r'session_id=([^;]+)').firstMatch(value);
          if (match != null) {
            sessionId = match.group(1);
          }
        }
      }
    });

    if (sessionId != null && responseString.contains('"result"')) {
      try {
        var jsonResponse = json.decode(responseString);
        if (jsonResponse is Map && jsonResponse['result'] is Map) {
          jsonResponse['result']['session_id'] = sessionId;
          responseString = json.encode(jsonResponse);
          responseBodyBytes = utf8.encode(responseString);
        }
      } catch (e) {
        // Not a valid JSON, ignore
      }
    }

    // Forward response headers
    request.response.statusCode = proxyResponse.statusCode;
    request.response.headers.add('Access-Control-Allow-Origin', '*');
    
    proxyResponse.headers.forEach((name, values) {
      if (name.toLowerCase() != 'access-control-allow-origin' && name.toLowerCase() != 'content-length' && name.toLowerCase() != 'transfer-encoding') {
        for (var value in values) {
          request.response.headers.add(name, value);
        }
      }
    });

    // Set correct content length
    request.response.headers.add('Content-Length', responseBodyBytes.length.toString());

    // Send response body
    request.response.add(responseBodyBytes);
    await request.response.close();
    client.close();
  } catch (e) {
    print('Error: $e');
    request.response.statusCode = HttpStatus.internalServerError;
    await request.response.close();
  }
}
