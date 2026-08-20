import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/odoo_api.dart';
import 'chat_screen.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:flutter_contacts/flutter_contacts.dart';


class ContactsSelectionScreen extends StatefulWidget {
  final String title;

  const ContactsSelectionScreen({super.key, required this.title});

  @override
  State<ContactsSelectionScreen> createState() => _ContactsSelectionScreenState();
}

class _ContactsSelectionScreenState extends State<ContactsSelectionScreen> {
  late Future<List<dynamic>> _contactsFuture;
  final Set<dynamic> _selectedContactIds = {};
  bool _isSearching = false;
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  List<dynamic> _cachedContacts = [];

  @override
  void initState() {
    super.initState();
    _contactsFuture = _fetchMergedContacts();
  }

  Future<List<dynamic>> _fetchMergedContacts() async {
    try {
      final status = await FlutterContacts.permissions.request(PermissionType.read);
      if (status == PermissionStatus.granted || status == PermissionStatus.limited) {
        final contacts = await FlutterContacts.getAll(properties: {ContactProperty.phone});
        final list = <Map<String, dynamic>>[];
        for (var c in contacts) {
          if (c.phones.isNotEmpty) {
            list.add({
              'id': c.id, 
              'name': c.displayName,
              'phone': c.phones.first.number,
              'is_device': true,
            });
          }
        }
        _cachedContacts = list;
        return list;
      }
    } catch (e) {
      debugPrint("Error fetching device contacts: $e");
    }

    final odooApi = Provider.of<OdooApi>(context, listen: false);
    try {
      final contacts = await odooApi.fetchContacts();
      _cachedContacts = contacts;
      return contacts;
    } catch (e) {
      debugPrint("Failed to fetch Odoo contacts: $e");
      return [];
    }
  }

  void _toggleSelection(dynamic id, String name, String phone) async {
    if (widget.title == 'Select contact' && _selectedContactIds.isEmpty) {

      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (_) => const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2))),
      );

      try {
        final api = Provider.of<OdooApi>(context, listen: false);
        int? odooId;
        if (id is String) {
          odooId = await api.syncSingleContactAndGetId(name, phone);
        } else {
          odooId = id as int;
        }

        if (odooId == null) throw Exception("Could not sync or find contact in Odoo.");

        final chat = await api.getOrCreateDirectChat(odooId);
        
        if (mounted) {
          Navigator.pop(context); // close loading
        }
        
        if (chat != null) {
          final channelId = chat['id'] as int;
          final channelName = chat['name'] as String? ?? name;
          
          if (mounted) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(
                builder: (_) => ChatScreen(
                  channelId: channelId,
                  channelName: channelName,
                  contactName: channelName,
                  customerPhone: phone,
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

  void _onLongPress(int id) {
    setState(() {
      if (_selectedContactIds.contains(id)) {
        _selectedContactIds.remove(id);
      } else {
        _selectedContactIds.add(id);
      }
    });
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: _isSearching
            ? TextField(
                controller: _searchController,
                autofocus: true,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  hintText: 'Search contacts...',
                  hintStyle: TextStyle(color: Colors.white70),
                  border: InputBorder.none,
                ),
                onChanged: (value) {
                  setState(() {
                    _searchQuery = value.toLowerCase();
                  });
                },
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(widget.title),
                  const Text('Select contacts', style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal)),
                ],
              ),
        backgroundColor: const Color(0xFF128C7E),
        foregroundColor: Colors.white,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (_isSearching) {
              setState(() {
                _isSearching = false;
                _searchQuery = '';
                _searchController.clear();
              });
            } else {
              Navigator.pop(context);
            }
          },
        ),
        actions: [
          if (!_isSearching)
            IconButton(
              icon: const Icon(Icons.search),
              onPressed: () {
                setState(() {
                  _isSearching = true;
                });
              },
            ),
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

          var contacts = snapshot.data ?? [];
          
          if (_searchQuery.isNotEmpty) {
            contacts = contacts.where((contact) {
              final name = (contact['name'] as String? ?? '').toLowerCase();
              final phone = (contact['phone']?.toString() ?? '').toLowerCase();
              final mobile = (contact['mobile']?.toString() ?? '').toLowerCase();
              return name.contains(_searchQuery) || phone.contains(_searchQuery) || mobile.contains(_searchQuery);
            }).toList();
          }

          if (contacts.isEmpty) {
            return const Center(child: Text('No contacts found'));
          }

          return ListView.builder(
            itemCount: contacts.length,
            itemBuilder: (context, index) {
              final contact = contacts[index];
              final id = contact['id'];
              final name = contact['name'] as String? ?? 'Unknown';
              final isCompany = contact['is_company'] == true;

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
                onTap: () {
                  if (_selectedContactIds.isNotEmpty) {
                    _toggleSelection(id, name, mobile.isNotEmpty ? mobile : phone);
                  } else {
                    _toggleSelection(id, name, mobile.isNotEmpty ? mobile : phone);
                  }
                },
                onLongPress: () => _onLongPress(id),
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
