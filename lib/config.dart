// lib/config.dart
// Default Odoo server URL. Can be overridden at compile time with
// `--dart-define=ODOO_SERVER=<your-url>`.
// If no definition is provided, it falls back to the demo server.

const String defaultOdooServerUrl = String.fromEnvironment(
  'ODOO_SERVER',
  defaultValue: 'https://demo1.havano.pro',
);
