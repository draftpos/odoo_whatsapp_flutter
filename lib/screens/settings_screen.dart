import 'package:flutter/material.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
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
        ],
      ),
    );
  }
}
