import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/odoo_api.dart';
import '../config.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _urlController = TextEditingController();
  final _dbController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _loadSavedAccount();
  }

  /// Pre-fill URL and DB from the last successful login stored in SharedPreferences.
  /// Falls back to the demo server values if nothing has been saved yet.
  Future<void> _loadSavedAccount() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _urlController.text =
          prefs.getString('odoo_url') ?? defaultOdooServerUrl;
      _dbController.text =
          prefs.getString('odoo_db') ?? '';
    });
  }

  @override
  void dispose() {
    _urlController.dispose();
    _dbController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    if (_usernameController.text.trim().isEmpty || _passwordController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter your username and password.')),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    final api = Provider.of<OdooApi>(context, listen: false);
    
    final success = await api.login(
      _urlController.text.trim(), 
      _dbController.text.trim(), 
      _usernameController.text.trim(),
      _passwordController.text,
    );

    setState(() {
      _isLoading = false;
    });

    if (success) {
      if (mounted) {
        // Option to fetch profile immediately to ensure phone number is ready
        await api.fetchCurrentUserProfile();
        
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => const HomeScreen(),
          ),
        );
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to login. Please check your credentials.'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          'Login to Odoo',
          style: TextStyle(color: Color(0xFF1976D2), fontWeight: FontWeight.bold),
        ),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert, color: Colors.grey),
            onSelected: (value) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('$value tapped (Coming soon)')),
              );
            },
            itemBuilder: (BuildContext context) {
              return {'Link as companion device', 'Help'}.map((String choice) {
                return PopupMenuItem<String>(
                  value: choice,
                  child: Text(choice),
                );
              }).toList();
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 16.0),
                child: Column(
                  children: [
                    const Text(
                      'Enter your Odoo credentials to connect your account.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 15, color: Colors.black87),
                    ),
                    const SizedBox(height: 32),

                    AutofillGroup(
                      child: Column(
                        children: [
                    // Server Config Section
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade50,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.grey.shade200),
                      ),
                      child: Column(
                        children: [
                          TextField(
                            controller: _urlController,
                            autofillHints: const [AutofillHints.url],
                            keyboardType: TextInputType.url,
                            decoration: InputDecoration(
                              labelText: 'Server URL',
                              labelStyle: const TextStyle(color: Color(0xFF1976D2)),
                              prefixIcon: const Icon(Icons.link, color: Colors.grey),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide.none,
                              ),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _dbController,
                            autofillHints: const [AutofillHints.organizationName],
                            decoration: InputDecoration(
                              labelText: 'Database Name',
                              labelStyle: const TextStyle(color: Color(0xFF1976D2)),
                              prefixIcon: const Icon(Icons.storage, color: Colors.grey),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide.none,
                              ),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),


                    // Credentials Section
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade50,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFF1976D2), width: 1.5),
                      ),
                      child: Column(
                        children: [
                          TextField(
                            controller: _usernameController,
                            autofillHints: const [AutofillHints.username],
                            keyboardType: TextInputType.emailAddress,
                            decoration: InputDecoration(
                              labelText: 'Username',
                              labelStyle: const TextStyle(color: Color(0xFF1976D2)),
                              prefixIcon: const Icon(Icons.person, color: Colors.grey),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide.none,
                              ),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            autofillHints: const [AutofillHints.password],
                            decoration: InputDecoration(
                              labelText: 'Password',
                              labelStyle: const TextStyle(color: Color(0xFF1976D2)),
                              prefixIcon: const Icon(Icons.lock, color: Colors.grey),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_off : Icons.visibility,
                                  color: Colors.grey,
                                ),
                                onPressed: () {
                                  setState(() {
                                    _obscurePassword = !_obscurePassword;
                                  });
                                },
                              ),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide.none,
                              ),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                          ),
                        ],
                      ),
                    ),
                        ],  // AutofillGroup column children
                      ),   // AutofillGroup column
                    ),     // AutofillGroup

                    const SizedBox(height: 16),
                    const Text(
                      'Your phone number will be automatically synced.',
                      style: TextStyle(fontSize: 13, color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _handleLogin,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1976D2),
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(25),
                    ),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          height: 24,
                          width: 24,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Text(
                          'LOGIN',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1.2,
                          ),
                        ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

