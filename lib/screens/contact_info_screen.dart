import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/odoo_api.dart';
import 'package:url_launcher/url_launcher.dart';

class ContactInfoScreen extends StatefulWidget {
  final int channelId;
  final String contactName;
  final String? customerPhone;
  final String? customerImage;

  const ContactInfoScreen({
    super.key,
    required this.channelId,
    required this.contactName,
    this.customerPhone,
    this.customerImage,
  });

  @override
  State<ContactInfoScreen> createState() => _ContactInfoScreenState();
}

class _ContactInfoScreenState extends State<ContactInfoScreen> {
  late Future<List<dynamic>> _mediaFuture;
  bool _isEditing = false;
  late TextEditingController _nameController;
  late String _currentName;

  @override
  void initState() {
    super.initState();
    _currentName = widget.contactName;
    _nameController = TextEditingController(text: _currentName);
    _mediaFuture = _fetchMedia();
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<List<dynamic>> _fetchMedia() async {
    final api = Provider.of<OdooApi>(context, listen: false);
    try {
      final domain = [
        ['res_model', '=', 'discuss.channel'],
        ['res_id', '=', widget.channelId]
      ];
      return await api.searchRead(
        'ir.attachment',
        domain,
        ['id', 'name', 'mimetype', 'create_date'],
        limit: 50,
      );
    } catch (e) {
      debugPrint('Error fetching channel media: $e');
      return [];
    }
  }

  String _channelAvatarUrl() {
    return 'https://ui-avatars.com/api/?name=${Uri.encodeComponent(widget.contactName)}&background=random';
  }

  void _openFile(int attachmentId, String name) async {
    final api = Provider.of<OdooApi>(context, listen: false);
    final url = '${api.baseUrl}/web/content/$attachmentId?download=true';
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open file')),
        );
      }
    }
  }

  void _saveName() async {
    final newName = _nameController.text.trim();
    if (newName.isEmpty || newName == _currentName) {
      setState(() {
        _isEditing = false;
      });
      return;
    }

    final api = Provider.of<OdooApi>(context, listen: false);
    final success = await api.updateContactName(widget.channelId, newName);
    
    if (success) {
      setState(() {
        _currentName = newName;
        _isEditing = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Contact name updated')),
        );
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update contact name')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F2F5),
      appBar: AppBar(
        title: const Text('Contact info'),
        backgroundColor: const Color(0xFF128C7E),
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Profile Info Section
            Container(
              width: double.infinity,
              color: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 30, horizontal: 20),
              margin: const EdgeInsets.only(bottom: 10),
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 70,
                    backgroundImage: widget.customerImage != null
                        ? NetworkImage('data:image/jpeg;base64,${widget.customerImage}')
                        : NetworkImage(_channelAvatarUrl()),
                  ),
                  const SizedBox(height: 20),
                  if (_isEditing)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          width: 200,
                          child: TextField(
                            controller: _nameController,
                            decoration: const InputDecoration(
                              isDense: true,
                              border: OutlineInputBorder(),
                            ),
                            onSubmitted: (_) => _saveName(),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.check, color: Colors.green),
                          onPressed: _saveName,
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, color: Colors.grey),
                          onPressed: () {
                            setState(() {
                              _nameController.text = _currentName;
                              _isEditing = false;
                            });
                          },
                        ),
                      ],
                    )
                  else
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _currentName,
                          style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w400, color: Colors.black87),
                        ),
                        IconButton(
                          icon: const Icon(Icons.edit, size: 20, color: Colors.grey),
                          onPressed: () {
                            setState(() {
                              _isEditing = true;
                            });
                          },
                        ),
                      ],
                    ),
                  const SizedBox(height: 10),
                  if (widget.customerPhone != null && widget.customerPhone!.isNotEmpty)
                    Text(
                      widget.customerPhone!,
                      style: const TextStyle(fontSize: 18, color: Colors.black54),
                    ),
                ],
              ),
            ),

            // Media Section
            Container(
              width: double.infinity,
              color: Colors.white,
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Media, links, and docs',
                    style: TextStyle(fontSize: 16, color: Color(0xFF128C7E), fontWeight: FontWeight.w500),
                  ),
                  const SizedBox(height: 15),
                  FutureBuilder<List<dynamic>>(
                    future: _mediaFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      
                      final mediaList = snapshot.data ?? [];
                      if (mediaList.isEmpty) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 20),
                          child: Text('No media found', style: TextStyle(color: Colors.black54)),
                        );
                      }

                      final images = mediaList.where((m) {
                        final mt = m['mimetype'] as String? ?? '';
                        return mt.startsWith('image/');
                      }).toList();

                      final others = mediaList.where((m) {
                        final mt = m['mimetype'] as String? ?? '';
                        return !mt.startsWith('image/');
                      }).toList();

                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (images.isNotEmpty) ...[
                            GridView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 3,
                                crossAxisSpacing: 5,
                                mainAxisSpacing: 5,
                              ),
                              itemCount: images.length,
                              itemBuilder: (context, index) {
                                final img = images[index];
                                final api = Provider.of<OdooApi>(context, listen: false);
                                final imgUrl = '${api.baseUrl}/web/image/${img['id']}';
                                return GestureDetector(
                                  onTap: () => _openFile(img['id'] as int, img['name'] as String? ?? ''),
                                  child: Container(
                                    color: Colors.grey.shade200,
                                    child: Image.network(imgUrl, fit: BoxFit.cover),
                                  ),
                                );
                              },
                            ),
                            const SizedBox(height: 20),
                          ],
                          if (others.isNotEmpty) ...[
                            ListView.builder(
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              itemCount: others.length,
                              itemBuilder: (context, index) {
                                final doc = others[index];
                                return ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  leading: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: Colors.red.shade400,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: const Icon(Icons.insert_drive_file, color: Colors.white),
                                  ),
                                  title: Text(doc['name'] as String? ?? 'Document', maxLines: 1, overflow: TextOverflow.ellipsis),
                                  subtitle: Text(doc['create_date'] as String? ?? ''),
                                  onTap: () => _openFile(doc['id'] as int, doc['name'] as String? ?? ''),
                                );
                              },
                            )
                          ]
                        ],
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
