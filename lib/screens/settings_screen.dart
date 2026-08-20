import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/odoo_api.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Map<String, dynamic>? _currentAccount;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAccount();
  }

  Future<void> _loadAccount() async {
    final api = Provider.of<OdooApi>(context, listen: false);
    try {
      final accounts = await api.searchRead(
        'whatsapp.account',
        [],
        ['id', 'name', 'wa_bot_active'],
      );
      if (accounts.isNotEmpty) {
        if (mounted) {
          setState(() {
            _currentAccount = accounts[0] as Map<String, dynamic>;
            _isLoading = false;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool botActive = _currentAccount != null && (_currentAccount!['wa_bot_active'] as bool? ?? false);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          const ListTile(
            leading: CircleAvatar(
              radius: 30,
              child: Icon(Icons.person, size: 40),
            ),
            title: Text('Profile'),
            subtitle: Text('Status'),
            trailing: Icon(Icons.qr_code, color: Color(0xFF1976D2)),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.key),
            title: const Text('Account'),
            subtitle: const Text('Security notifications, change number'),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.lock),
            title: const Text('Privacy'),
            subtitle: const Text('Block contacts, disappearing messages'),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.chat),
            title: const Text('Chats'),
            subtitle: const Text('Theme, wallpapers, chat history'),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.notifications),
            title: const Text('Notifications'),
            subtitle: const Text('Message, group & call tones'),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.help_outline),
            title: const Text('Help'),
            subtitle: const Text('Help center, contact us, privacy policy'),
            onTap: () {},
          ),
          if (!_isLoading && _currentAccount != null) ...[
            const Divider(),
            SwitchListTile(
              secondary: const Icon(Icons.smart_toy),
              title: const Text('Automated Bot Responses'),
              subtitle: Text('Manage bot for ${_currentAccount!['name']}'),
              value: botActive,
              onChanged: (val) async {
                final api = Provider.of<OdooApi>(context, listen: false);
                setState(() {
                  _currentAccount!['wa_bot_active'] = val;
                });
                final success = await api.toggleAccountBot(_currentAccount!['id'] as int, val);
                if (!success) {
                  if (mounted) {
                    setState(() {
                      _currentAccount!['wa_bot_active'] = !val;
                    });
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Failed to toggle bot')),
                    );
                  }
                }
              },
            ),
          ],
        ],
      ),
    );
  }
}
