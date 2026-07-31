import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/login_screen.dart';
import 'services/odoo_api.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove('odoo_session_id'); // Force fresh login

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => OdooApi()),
      ],
      child: const WhatsAppCloneApp(),
    ),
  );
}

class WhatsAppCloneApp extends StatelessWidget {
  const WhatsAppCloneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Havano OdooWhatsapp',
      theme: ThemeData(
        primaryColor: const Color(0xFF0D47A1),
        colorScheme: ColorScheme.fromSwatch().copyWith(
          secondary: const Color(0xFF1976D2),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0D47A1),
          foregroundColor: Colors.white,
        ),
      ),
      home: const LoginScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
