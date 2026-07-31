import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/odoo_api.dart';
import 'chat_screen.dart';
import 'login_screen.dart';
import 'settings_screen.dart';
import 'linked_devices_screen.dart';
import 'starred_messages_screen.dart';
import 'contacts_selection_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<dynamic>> _chatsFuture;
  late Future<Map<String, dynamic>?> _adminPartnerFuture;
  late Future<List<dynamic>> _contactsFuture;
  List<dynamic> _accounts = [];
  int? _selectedAccountId;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
  }

  Future<void> _loadInitialData() async {
    final api = Provider.of<OdooApi>(context, listen: false);
    final accounts = await api.fetchAccounts();
    int? initialAccountId;
    if (accounts.isNotEmpty) {
      initialAccountId = accounts[0]['id'] as int;
    }
    
    setState(() {
      _accounts = accounts;
      _selectedAccountId = initialAccountId;
      _chatsFuture = api.fetchChats(accountId: _selectedAccountId);
      _adminPartnerFuture = api.fetchAdminPartner();
      _contactsFuture = api.fetchContacts();
    });
  }

  Future<void> _refreshChats() async {
    final api = Provider.of<OdooApi>(context, listen: false);
    setState(() {
      _chatsFuture = api.fetchChats(accountId: _selectedAccountId);
      _adminPartnerFuture = api.fetchAdminPartner();
      _contactsFuture = api.fetchContacts();
    });
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      initialIndex: 1,
      child: Scaffold(
        appBar: AppBar(
          title: _accounts.isNotEmpty
              ? DropdownButton<int>(
                  value: _selectedAccountId,
                  dropdownColor: Theme.of(context).primaryColor,
                  icon: const Icon(Icons.arrow_drop_down, color: Colors.white),
                  underline: const SizedBox(),
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  onChanged: (int? newValue) {
                    if (newValue != null && newValue != _selectedAccountId) {
                      setState(() {
                        _selectedAccountId = newValue;
                        _chatsFuture = Provider.of<OdooApi>(context, listen: false).fetchChats(accountId: _selectedAccountId);
                      });
                    }
                  },
                  items: _accounts.map<DropdownMenuItem<int>>((dynamic acc) {
                    return DropdownMenuItem<int>(
                      value: acc['id'] as int,
                      child: Text(acc['name'] as String? ?? 'Account'),
                    );
                  }).toList(),
                )
              : const Text('Havano OdooWhatsapp'),
          actions: [
            IconButton(
              icon: const Icon(Icons.search),
              onPressed: () {
                showSearch(context: context, delegate: _ChatSearchDelegate(_chatsFuture));
              },
            ),
            PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'Logout') {
                  await Provider.of<OdooApi>(context, listen: false).logout();
                  if (context.mounted) {
                    Navigator.of(context).pushAndRemoveUntil(
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                      (Route<dynamic> route) => false,
                    );
                  }
                } else if (value == 'Settings') {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
                } else if (value == 'Linked devices') {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LinkedDevicesScreen()));
                } else if (value == 'Starred messages') {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const StarredMessagesScreen()));
                } else if (value == 'New group') {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ContactsSelectionScreen(title: 'New group')));
                } else if (value == 'New broadcast') {
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ContactsSelectionScreen(title: 'New broadcast')));
                }
              },
              itemBuilder: (BuildContext context) {
                return {
                  'New group',
                  'New broadcast',
                  'Linked devices',
                  'Starred messages',
                  'Settings',
                  'Logout'
                }.map((String choice) {
                  return PopupMenuItem<String>(
                    value: choice,
                    child: Text(choice),
                  );
                }).toList();
              },
            ),
          ],
          bottom: TabBar(
            indicatorColor: Colors.white,
            indicatorWeight: 3,
            labelStyle: const TextStyle(fontWeight: FontWeight.bold),
            tabs: [
              const Tab(icon: Icon(Icons.camera_alt)),
              Tab(
                child: FutureBuilder<List<dynamic>>(
                  future: _chatsFuture,
                  builder: (context, snapshot) {
                    int unreadChats = 0;
                    if (snapshot.hasData) {
                      for (var chat in snapshot.data!) {
                        final count = chat['message_needaction_counter'] as int? ?? 0;
                        if (count > 0) unreadChats++;
                      }
                    }
                    
                    if (unreadChats > 0) {
                      return Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text('CHATS'),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: const BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.all(Radius.circular(10)),
                            ),
                            child: Text(
                              unreadChats.toString(),
                              style: TextStyle(
                                color: Theme.of(context).primaryColor, 
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      );
                    }
                    return const Text('CHATS');
                  },
                ),
              ),
              const Tab(text: 'STATUS'),
              const Tab(text: 'CALLS'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _buildCameraMockup(),
            RefreshIndicator(
              onRefresh: _refreshChats,
              child: _buildRealChatsList(),
            ),
            _buildStatusMockup(),
            _buildCallsMockup(),
          ],
        ),
        floatingActionButton: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            FloatingActionButton(
              heroTag: 'catalogue',
              onPressed: () => _showCatalogue(context),
              backgroundColor: Colors.white,
              child: const Icon(Icons.storefront, color: Color(0xFF1976D2)),
            ),
            const SizedBox(height: 16),
            FloatingActionButton(
              heroTag: 'new_chat',
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const ContactsSelectionScreen(title: 'Select contact'),
                  ),
                ).then((_) => _refreshChats());
              },
              backgroundColor: Theme.of(context).colorScheme.secondary,
              child: const Icon(Icons.message, color: Colors.white),
            ),
          ],
        ),
      ),
    );
  }

  void _showCatalogue(BuildContext context) async {
    final api = Provider.of<OdooApi>(context, listen: false);
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Product Catalogue', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: FutureBuilder<List<dynamic>>(
                  future: api.fetchProducts(),
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError || !snapshot.hasData || snapshot.data!.isEmpty) {
                      return const Center(child: Text('No products available', style: TextStyle(color: Colors.grey)));
                    }
                    final products = snapshot.data!;
                    return GridView.builder(
                      padding: const EdgeInsets.all(8.0),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        crossAxisSpacing: 10,
                        mainAxisSpacing: 10,
                        childAspectRatio: 0.8,
                      ),
                      itemCount: products.length,
                      itemBuilder: (context, index) {
                        final p = products[index];
                        final imgBase64 = p['image_128'];
                        return Card(
                          clipBehavior: Clip.antiAlias,
                          child: InkWell(
                            onTap: () {
                              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Selected: ${p['name']}')));
                            },
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Expanded(
                                  child: imgBase64 != null && imgBase64 != false
                                      ? Image.memory(
                                          base64Decode(imgBase64 as String),
                                          fit: BoxFit.cover,
                                        )
                                      : Container(
                                          color: Colors.grey.shade200,
                                          child: const Icon(Icons.image, size: 50, color: Colors.grey),
                                        ),
                                ),
                                Padding(
                                  padding: const EdgeInsets.all(8.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(p['name'].toString(), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.bold)),
                                      const SizedBox(height: 4),
                                      Text('\$${(p['list_price'] ?? 0.0).toString()}', style: TextStyle(color: Colors.green.shade700)),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCameraMockup() {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.camera_alt, size: 80, color: Colors.white54),
            const SizedBox(height: 16),
            const Text(
              'Camera access required',
              style: TextStyle(color: Colors.white, fontSize: 18),
            ),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Camera plugin needed for web.')));
              },
              child: const Text('Allow'),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildCallsMockup() {
    return FutureBuilder<List<dynamic>>(
      future: _contactsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2)));
        }

        final contacts = snapshot.data ?? [];
        final callableContacts = contacts.where((c) => c['phone'] != false && c['phone'] != null).toList();

        return ListView(
          children: [
            const ListTile(
              leading: CircleAvatar(
                backgroundColor: Color(0xFF1976D2),
                child: Icon(Icons.link, color: Colors.white),
              ),
              title: Text('Create call link', style: TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text('Share a link for your WhatsApp call'),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: Text('Recent', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
            ),
            if (callableContacts.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Center(child: Text('No contacts with phone numbers found.', style: TextStyle(color: Colors.grey))),
              ),
            ...callableContacts.map((contact) {
              final phone = (contact['phone'] != false ? contact['phone'] : '').toString();
              return ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Colors.grey,
                  child: Icon(Icons.person, color: Colors.white),
                ),
                title: Text(contact['name'].toString(), style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Row(
                  children: [
                    const Icon(Icons.call_made, color: Color(0xFF1976D2), size: 16),
                    const SizedBox(width: 4),
                    Text(phone),
                  ],
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.call, color: Color(0xFF1976D2)),
                  onPressed: () {
                     // Removed url_launcher to simplify
                  },
                ),
              );
            }).toList(),
          ],
        );
      },
    );
  }

  Widget _buildStatusMockup() {
    return FutureBuilder<List<dynamic>>(
      future: _contactsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2)));
        }

        final contacts = snapshot.data ?? [];
        final recentContacts = contacts.take(5).toList();

        return ListView(
          padding: const EdgeInsets.all(8),
          children: [
            ListTile(
              leading: Stack(
                children: [
                  const CircleAvatar(
                    radius: 24,
                    backgroundColor: Colors.grey,
                    child: Icon(Icons.person, color: Colors.white),
                  ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      decoration: const BoxDecoration(
                        color: Color(0xFF1976D2),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.add, color: Colors.white, size: 20),
                    ),
                  ),
                ],
              ),
              title: const Text('My status', style: TextStyle(fontWeight: FontWeight.bold)),
              subtitle: const Text('Tap to add status update'),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Text('Recent updates', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
            ),
            if (recentContacts.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Text('No recent updates.', style: TextStyle(color: Colors.grey)),
              ),
            ...recentContacts.map((contact) {
              return ListTile(
                leading: const CircleAvatar(
                  radius: 24,
                  backgroundColor: Color(0xFF1976D2),
                  child: CircleAvatar(
                    radius: 22,
                    backgroundColor: Colors.grey,
                    child: Icon(Icons.person, color: Colors.white),
                  ),
                ),
                title: Text(contact['name'].toString(), style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: const Text('Today, 10:30 AM'),
              );
            }).toList(),
          ],
        );
      },
    );
  }

  Widget _buildRealChatsList() {
    return FutureBuilder(
      future: Future.wait([_chatsFuture, _adminPartnerFuture]),
      builder: (context, AsyncSnapshot<List<dynamic>> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2)));
        }

        if (snapshot.hasError) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                 const Icon(Icons.error_outline, size: 64, color: Colors.grey),
                 const SizedBox(height: 16),
                 Text('Error loading chats: ${snapshot.error}', style: const TextStyle(color: Colors.grey)),
                 ElevatedButton(onPressed: _refreshChats, child: const Text('Retry'))
              ]
            )
          );
        }

        final rawChats = snapshot.data![0] as List<dynamic>;
        final adminPartner = snapshot.data![1] as Map<String, dynamic>?;
        
        final adminName = adminPartner?['name'] as String? ?? '';
        
        // We will simply filter out internal chats named "Direct Message" 
        // to remove the clutter, and let all actual named chats (including WhatsApp) show up.
        final List<dynamic> chats = rawChats.where((chat) {
          final name = chat['name'] as String? ?? '';
          final type = chat['channel_type'] as String? ?? '';
          
          // Hide the generic duplicate Odoo internal chats
          if (type == 'chat' && name == 'Direct Message') {
            return false;
          }
          return true;
        }).toList();

        if (chats.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.chat_bubble_outline, size: 64, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('No chats found.', style: TextStyle(fontSize: 18, color: Colors.grey)),
                const SizedBox(height: 8),
                const Text('Start a new chat using the button below.', style: TextStyle(color: Colors.grey)),
                const SizedBox(height: 16),
                TextButton(onPressed: _refreshChats, child: const Text('Refresh', style: TextStyle(color: Color(0xFF1976D2))))
              ],
            ),
          );
        }

        return ListView.builder(
          itemCount: chats.length,
          itemBuilder: (context, index) {
            final chat = chats[index];
            final channelId = chat['id'] as int;
            final channelName = chat['name'] as String? ?? 'Unknown Chat';
            final channelType = chat['channel_type'] as String? ?? '';
            final unreadCount = chat['message_needaction_counter'] as int? ?? 0;
            final whatsappNumber = chat['whatsapp_number'] is String ? chat['whatsapp_number'] as String : null;
            final isWhatsapp = channelType == 'whatsapp';

            final subtitle = channelType == 'channel'
                    ? 'Group channel'
                    : isWhatsapp && whatsappNumber != null && whatsappNumber.isNotEmpty
                        ? 'WhatsApp: $whatsappNumber'
                        : 'Tap to open chat';

            // Format write_date to a readable time
            final rawDate = chat['write_date'];
            String timeStr = '';
            if (rawDate != null && rawDate != false) {
              try {
                final dt = DateTime.parse(rawDate.toString()).toLocal();
                final now = DateTime.now();
                final diff = now.difference(dt);
                if (diff.inMinutes < 60) {
                  timeStr = '${diff.inMinutes}m ago';
                } else if (diff.inHours < 24) {
                  timeStr =
                      '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
                } else {
                  timeStr = '${dt.day}/${dt.month}';
                }
              } catch (_) {}
            }

            final customerImage = chat['customer_image'] is String ? chat['customer_image'] as String : null;
            final customerPhone = chat['customer_phone'] is String ? chat['customer_phone'] as String : null;

            return ListTile(
              leading: customerImage != null
                  ? CircleAvatar(
                      backgroundImage: MemoryImage(base64Decode(customerImage)),
                      backgroundColor: Colors.transparent,
                    )
                  : CircleAvatar(
                      backgroundColor: isWhatsapp
                          ? const Color(0xFF25D366)   // WhatsApp green
                          : channelType == 'channel'
                              ? const Color(0xFF1976D2)
                              : Colors.grey.shade500,
                      child: Icon(
                        isWhatsapp
                            ? Icons.phone_android
                            : channelType == 'channel'
                                ? Icons.group
                                : Icons.chat_bubble,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
              title: Text(channelName,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              subtitle: Text(subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.grey)),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (timeStr.isNotEmpty)
                    Text(timeStr, style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  if (unreadCount > 0)
                    Container(
                      margin: const EdgeInsets.only(top: 4),
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      decoration: BoxDecoration(
                        color: isWhatsapp ? const Color(0xFF25D366) : const Color(0xFF1976D2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        unreadCount.toString(),
                        style: const TextStyle(
                            color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    ),
                ],
              ),
              onTap: () async {
                // Open chat within the app
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ChatScreen(
                      channelId: channelId,
                      channelName: channelName,
                      contactName: channelName,
                      isWhatsapp: isWhatsapp,
                      customerImage: customerImage,
                      customerPhone: customerPhone,
                      waAccountId: chat['wa_account_id'] != null && chat['wa_account_id'].isNotEmpty ? chat['wa_account_id'][0] as int : null,
                    ),
                  ),
                ).then((_) => _refreshChats());
              },
            );
          },
        );
      },
    );
  }
}

// Search Delegate for filtering chats
class _ChatSearchDelegate extends SearchDelegate {
  final Future<List<dynamic>> chatsFuture;

  _ChatSearchDelegate(this.chatsFuture);

  @override
  List<Widget>? buildActions(BuildContext context) {
    return [
      IconButton(
        icon: const Icon(Icons.clear),
        onPressed: () {
          query = '';
        },
      )
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.arrow_back),
      onPressed: () {
        close(context, null);
      },
    );
  }

  @override
  Widget buildResults(BuildContext context) {
    return _buildList();
  }

  @override
  Widget buildSuggestions(BuildContext context) {
    return _buildList();
  }

  Widget _buildList() {
    return FutureBuilder<List<dynamic>>(
      future: chatsFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const SizedBox();
        
        final allChats = snapshot.data!;
        final filteredChats = allChats.where((chat) {
          final name = (chat['name'] as String? ?? '').toLowerCase();
          return name.contains(query.toLowerCase());
        }).toList();

        return ListView.builder(
          itemCount: filteredChats.length,
          itemBuilder: (context, index) {
            final chat = filteredChats[index];
            final channelName = chat['name'] as String? ?? 'Unknown Chat';
            return ListTile(
              leading: const CircleAvatar(backgroundColor: Colors.grey, child: Icon(Icons.person, color: Colors.white)),
              title: Text(channelName, style: const TextStyle(fontWeight: FontWeight.bold)),
              onTap: () async {
                close(context, null);
                final channelId = chat['id'] as int;
                final channelName = chat['name'] as String? ?? 'Chat';
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ChatScreen(
                      channelId: channelId,
                      channelName: channelName,
                      contactName: channelName,
                      customerPhone: chat['customer_phone'] as String?,
                    ),
                  ),
                );
              },
            );
          },
        );
      },
    );
  }
}
