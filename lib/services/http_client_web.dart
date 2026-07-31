// Web platform: BrowserClient with withCredentials=true so the browser
// sends the Odoo session cookie on cross-origin requests.
// ignore: avoid_web_libraries_in_flutter
import 'package:http/browser_client.dart';
import 'package:http/http.dart' as http;

http.Client createHttpClient() {
  final client = BrowserClient();
  client.withCredentials = true;
  return client;
}
