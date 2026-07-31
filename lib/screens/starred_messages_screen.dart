import 'package:flutter/material.dart';

class StarredMessagesScreen extends StatelessWidget {
  const StarredMessagesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Starred messages'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF1976D2).withOpacity(0.1),
              ),
              child: const Icon(Icons.star, size: 80, color: Color(0xFF1976D2)),
            ),
            const SizedBox(height: 24),
            const Text(
              'No starred messages',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                'Tap and hold on any message in any chat to star it, so you can easily find it later.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
