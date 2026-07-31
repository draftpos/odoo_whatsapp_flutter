import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/odoo_api.dart';
import 'chat_screen.dart';
import 'package:url_launcher/url_launcher.dart';


class ContactsSelectionScreen extends StatefulWidget {
  final String title;

  const ContactsSelectionScreen({super.key, required this.title});

  @override
  State<ContactsSelectionScreen> createState() => _ContactsSelectionScreenState();
}

class _ContactsSelectionScreenState extends State<ContactsSelectionScreen> {
  late Future<List<dynamic>> _contactsFuture;
  final Set<int> _selectedContactIds = {};

  @override
  void initState() {
    super.initState();
    _contactsFuture = Provider.of<OdooApi>(context, listen: false).fetchContacts();
  }

  void _toggleSelection(int id, String name, String phone) async {
    if (widget.title == 'Select contact') {
      // Show loading indicator (cannot use typical showDialog easily without BuildContext, but we are in State so we can use context)
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2))),
      );

      try {
        final chat = await Provider.of<OdooApi>(context, listen: false).getOrCreateDirectChat(id);
        
        if (mounted) {
          Navigator.pop(context); // close loading
        }
        
        if (chat != null) {
          final channelId = chat['id'] as int;
          final channelName = chat['name'] as String? ?? name;
          
          if (mounted) {
            // Replace the selection screen with the chat screen
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(
                builder: (_) => ChatScreen(
                  channelId: channelId,
                  channelName: channelName,
                  contactName: channelName,
                ),
              ),
            );
          }
        } else {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Could not open direct chat.')),
            );
          }
        }
      } catch (e) {
        if (mounted) {
          Navigator.pop(context);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error: $e')),
          );
        }
      }
    } else {
      setState(() {
        if (_selectedContactIds.contains(id)) {
          _selectedContactIds.remove(id);
        } else {
          _selectedContactIds.add(id);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.title),
            const Text('Add participants', style: TextStyle(fontSize: 13, fontWeight: FontWeight.normal)),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.search), onPressed: () {}),
        ],
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _contactsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2)));
          }

          if (snapshot.hasError) {
            return const Center(child: Text('Failed to load contacts'));
          }

          final contacts = snapshot.data ?? [];

          if (contacts.isEmpty) {
            return const Center(child: Text('No contacts found'));
          }

          return ListView.builder(
            itemCount: contacts.length,
            itemBuilder: (context, index) {
              final contact = contacts[index];
              final id = contact['id'] as int;
              final name = contact['name'] as String? ?? 'Unknown';
              final isCompany = contact['is_company'] == true;

              // Odoo returns `false` (not null) when a field is empty
              final rawPhone = contact['phone'];
              final rawMobile = contact['mobile'];
              final rawEmail = contact['email'];
              final phone = (rawPhone != false && rawPhone != null) ? rawPhone.toString() : '';
              final mobile = (rawMobile != false && rawMobile != null) ? rawMobile.toString() : '';
              final email = (rawEmail != false && rawEmail != null) ? rawEmail.toString() : '';

              final subtitle = phone.isNotEmpty
                  ? phone
                  : mobile.isNotEmpty
                      ? mobile
                      : email.isNotEmpty
                          ? email
                          : null;

              final isSelected = _selectedContactIds.contains(id);

              return ListTile(
                leading: Stack(
                  children: [
                    CircleAvatar(
                      backgroundColor: isCompany
                          ? const Color(0xFF1565C0)
                          : Colors.grey.shade400,
                      child: Icon(
                        isCompany ? Icons.business : Icons.person,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
                    if (isSelected)
                      Positioned(
                        bottom: 0,
                        right: 0,
                        child: Container(
                          decoration: const BoxDecoration(
                            color: Color(0xFF1976D2),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.check, color: Colors.white, size: 16),
                        ),
                      ),
                  ],
                ),
                title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: subtitle != null ? Text(subtitle, style: const TextStyle(color: Colors.grey)) : null,
                onTap: () => _toggleSelection(id, name, mobile.isNotEmpty ? mobile : phone),
              );
            },
          );

        },
      ),
      floatingActionButton: _selectedContactIds.isNotEmpty && widget.title != 'Select contact'
          ? FloatingActionButton(
              backgroundColor: const Color(0xFF1976D2),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Group/Broadcast creation requires Odoo backend module support.')),
                );
              },
              child: const Icon(Icons.arrow_forward, color: Colors.white),
            )
          : null,
    );
  }
}
