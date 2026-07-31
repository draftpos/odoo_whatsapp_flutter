import 'package:flutter/material.dart';

class LinkedDevicesScreen extends StatelessWidget {
  const LinkedDevicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Linked devices'),
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const Icon(Icons.devices, size: 80, color: Color(0xFF1976D2)),
                const SizedBox(height: 16),
                const Text(
                  'Use WhatsApp on Web, Desktop, and other devices.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1976D2),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    child: const Text('Link a device'),
                  ),
                ),
              ],
            ),
          ),
          const Divider(thickness: 8, color: Color(0xFFF5F5F5)),
        ],
      ),
    );
  }
}
