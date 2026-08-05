import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/odoo_api.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:convert';
import 'login_screen.dart';
import 'package:url_launcher/url_launcher.dart';

class ChatScreen extends StatefulWidget {
  final int channelId;
  final String channelName;
  final String contactName;
  final bool isHomeScreen;
  final bool isWhatsapp;
  final String? customerImage;
  final String? customerPhone;
  final int? waAccountId;

  const ChatScreen({
    super.key,
    required this.channelId,
    required this.channelName,
    required this.contactName,
    this.isHomeScreen = false,
    this.isWhatsapp = false,
    this.customerImage,
    this.customerPhone,
    this.waAccountId,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  late Future<List<dynamic>> _messagesFuture;
  List<dynamic> _currentMessages = [];
  bool _isUploading = false;
  PlatformFile? _pendingFile;
  Timer? _refreshTimer;
  int? _currentAccountId;
  List<dynamic> _accounts = [];

  @override
  void initState() {
    super.initState();
    _currentAccountId = widget.waAccountId;
    final api = Provider.of<OdooApi>(context, listen: false);
    api.fetchAccounts().then((accounts) {
      if (mounted) {
        setState(() {
          _accounts = accounts;
        });
      }
    });
    _loadMessages();
    // Set up periodic refresh every 5 seconds to fetch new messages
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (mounted) {
        _loadMessages();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _loadMessages() {
    _messagesFuture = Provider.of<OdooApi>(context, listen: false).fetchMessages(widget.channelId);
    _messagesFuture.then((msgs) {
      if (mounted) {
        setState(() {
          _currentMessages = msgs;
        });
        _scrollToBottom();
      }
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _pickFile() async {
    FilePickerResult? result = await FilePicker.pickFiles(
      withData: true,
    );
    if (result != null && result.files.single.bytes != null) {
      setState(() {
        _pendingFile = result.files.single;
      });
    }
  }

  void _pickImage() async {
    FilePickerResult? result = await FilePicker.pickFiles(
      withData: true,
      type: FileType.image,
    );
    if (result != null && result.files.single.bytes != null) {
      setState(() {
        _pendingFile = result.files.single;
      });
    }
  }

  void _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty && _pendingFile == null) return;

    _messageController.clear();
    final fileToSend = _pendingFile;
    
    setState(() {
      _pendingFile = null;
      _currentMessages.add({
        'id': 0, // temp
        'body': '<p>${text.isNotEmpty ? text : (fileToSend != null ? "File: ${fileToSend.name}" : "")}</p>',
        'author_id': false, 
        'date': DateTime.now().toIso8601String(),
        'isMe': true,
      });
      if (fileToSend != null) {
        _isUploading = true;
      }
    });
    _scrollToBottom();

    final api = Provider.of<OdooApi>(context, listen: false);
    int? attachmentId;

    if (fileToSend != null && fileToSend.bytes != null) {
      final base64Data = base64Encode(fileToSend.bytes!);
      attachmentId = await api.uploadAttachment(fileToSend.name, base64Data);
    }

    final success = await api.sendMessage(
      widget.channelId, 
      text.isNotEmpty ? text : (fileToSend != null ? 'File: ${fileToSend.name}' : ''), 
      attachmentIds: attachmentId != null ? [attachmentId] : null,
      isWhatsapp: widget.isWhatsapp
    );
    
    if (success) {
      _loadMessages();
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to send message.')),
        );
      }
    }

    if (fileToSend != null && mounted) {
      setState(() {
        _isUploading = false;
      });
    }
  }

  String _stripHtml(String htmlString) {
    String processedHtml = htmlString
        .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
        .replaceAll(RegExp(r'</div>', caseSensitive: false), '\n')
        .replaceAll(RegExp(r'</p>', caseSensitive: false), '\n\n')
        .replaceAll(RegExp(r'</li>', caseSensitive: false), '\n');
    RegExp exp = RegExp(r"<[^>]*>", multiLine: true, caseSensitive: true);
    processedHtml = processedHtml.replaceAll(exp, '').replaceAll('&nbsp;', ' ');
    
    // Decode common HTML entities
    processedHtml = processedHtml
        .replaceAll('&gt;', '>')
        .replaceAll('&lt;', '<')
        .replaceAll('&amp;', '&');
        
    String text = processedHtml.trim();
    
    // Remove legacy sender prefixes like ">Bot: ", ">Customer: ", or ">John Doe: "
    final prefixMatch = RegExp(r'^>?[^:]+:\s*').firstMatch(text);
    if (prefixMatch != null && prefixMatch.start == 0) {
      // Check if it looks like a prefix
      final prefix = text.substring(0, prefixMatch.end);
      if (prefix.startsWith('>') || prefix.startsWith('Bot:') || prefix.startsWith('Customer:')) {
        text = text.substring(prefixMatch.end);
      }
    }
    
    return text.trim();
  }

  String _channelAvatarUrl() {
    return 'https://ui-avatars.com/api/?name=${Uri.encodeComponent(widget.contactName)}&background=random';
  }

  Future<void> _makeCall(bool isVideo) async {
    if (widget.customerPhone != null && widget.customerPhone!.isNotEmpty) {
      final url = Uri.parse('tel:${widget.customerPhone}');
      if (await canLaunchUrl(url)) {
        await launchUrl(url);
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not launch phone dialer')),
          );
        }
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No phone number found for this contact.')),
        );
      }
    }
  }

  void _showCatalogue() async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return _CatalogueSheet(
          onProductSelected: (product) {
            final priceStr = product['list_price'] != null ? '\$${product['list_price']}' : '';
            final text = 'Check out this product: ${product['name']} $priceStr';
            _messageController.text = text;
            Navigator.pop(context);
          },
        );
      },
    );
  }

  void _showTemplates() async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return _TemplatesSheet(
          onTemplateSelected: (template) {
            String text = template['body'] as String? ?? '';
            text = text.replaceAll(RegExp(r'\{\{\d+\}\}'), '');
            _messageController.text = text;
            Navigator.pop(context);
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: Colors.white24,
              child: Text(
                widget.channelName.isNotEmpty ? widget.channelName[0].toUpperCase() : '?',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.channelName,
                    style: const TextStyle(fontSize: 16),
                  ),
                  const Text('Online', style: TextStyle(fontSize: 12, color: Colors.white70)),
                ],
              ),
            ),
            if (_accounts.isNotEmpty)
              DropdownButtonHideUnderline(
                child: DropdownButton<int>(
                  value: _currentAccountId,
                  icon: const Icon(Icons.arrow_drop_down, color: Colors.white),
                  dropdownColor: Theme.of(context).primaryColor,
                  style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  onChanged: (int? newValue) {
                    if (newValue != null && newValue != _currentAccountId) {
                      setState(() {
                        _currentAccountId = newValue;
                        // Ideally, we'd update the wa_account_id on the Odoo backend here
                        // For now, we update the UI to show the selected account
                      });
                    }
                  },
                  items: _accounts.map<DropdownMenuItem<int>>((dynamic acc) {
                    return DropdownMenuItem<int>(
                      value: acc['id'] as int,
                      child: Text(acc['name'] as String? ?? 'Account'),
                    );
                  }).toList(),
                ),
              ),
          ],
        ),
        actions: [
          IconButton(icon: const Icon(Icons.videocam), onPressed: () => _makeCall(true)),
          IconButton(icon: const Icon(Icons.call), onPressed: () => _makeCall(false)),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'Logout') {
                await Provider.of<OdooApi>(context, listen: false).logout();
                if (mounted) {
                  Navigator.of(context).pushAndRemoveUntil(
                    MaterialPageRoute(builder: (_) => const LoginScreen()),
                    (Route<dynamic> route) => false,
                  );
                }
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('$value tapped (Coming soon)')),
                );
              }
            },
            itemBuilder: (BuildContext context) {
              final options = [
                'View contact',
                'Media, links, and docs',
                'Search',
                'Mute notifications',
                'Disappearing messages',
                'Wallpaper',
                'More'
              ];
              if (widget.isHomeScreen) {
                options.add('Logout');
              }
              return options.map((String choice) {
                return PopupMenuItem<String>(
                  value: choice,
                  child: Text(choice),
                );
              }).toList();
            },
          ),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(
          color: Color(0xFFF5F5F5),
          image: DecorationImage(
            image: NetworkImage('https://i.pinimg.com/736x/8c/98/99/8c98994518b575bfd8c949e91d20548b.jpg'),
            fit: BoxFit.cover,
          ),
        ),
        child: Column(
          children: [
            Expanded(
              child: FutureBuilder<List<dynamic>>(
                future: _messagesFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting && _currentMessages.isEmpty) {
                    return const Center(child: CircularProgressIndicator(color: Color(0xFF1976D2)));
                  }

                  if (_currentMessages.isEmpty) {
                    return Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: const BoxDecoration(
                          color: Color(0xFFE3F2FD),
                          borderRadius: BorderRadius.all(Radius.circular(8)),
                        ),
                        child: const Text(
                          'Send a message to start the conversation.',
                          style: TextStyle(fontSize: 13, color: Colors.black87),
                          textAlign: TextAlign.center,
                        ),
                      ),
                    );
                  }

                  final odooApi = Provider.of<OdooApi>(context, listen: false);
                  final myPartnerId = odooApi.partnerId;

                  return ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(8),
                    itemCount: _currentMessages.length,
                    itemBuilder: (context, index) {
                      // Odoo returns newest messages first or last depending on search. 
                      // Usually we might need to reverse, but let's stick to current order.
                      final message = _currentMessages[index];
                      final author = message['author_id'];
                      
                      bool isMe = false;
                      String authorName = "";
                      if (author is List && author.length > 1) {
                        authorName = author[1].toString().toLowerCase();
                      }

                      if (message['isMe'] == true) {
                        isMe = true;
                      } else if (author is List && author.isNotEmpty && author[0] == myPartnerId) {
                        isMe = true;
                      } else if (authorName.contains('bot') || authorName == 'odoobot' || authorName == 'system') {
                        isMe = true;
                      } else if (author == false) {
                        isMe = false; // Unsaved numbers have no author, so it's from them
                      }

                      final bodyHtml = message['body'] as String? ?? '';
                      final bodyText = _stripHtml(bodyHtml);

                      if (bodyHtml.contains('>Bot: ') || bodyHtml.contains('&gt;Bot: ') || bodyText.startsWith('Bot: ')) {
                          isMe = true;
                      } else if (bodyHtml.contains('>Customer: ') || bodyHtml.contains('&gt;Customer: ') || bodyText.startsWith('Customer: ')) {
                          isMe = false;
                      }

                      String timeText = '';
                      if (message['date'] != null) {
                        try {
                           // Odoo dates are UTC string like "2024-07-24 10:00:00"
                           String dateStr = message['date'];
                           if (!dateStr.endsWith('Z')) dateStr += 'Z'; // Force UTC parsing
                           final dt = DateTime.parse(dateStr).toLocal();
                           final hour = dt.hour > 12 ? dt.hour - 12 : (dt.hour == 0 ? 12 : dt.hour);
                           final ampm = dt.hour >= 12 ? 'PM' : 'AM';
                           final minute = dt.minute.toString().padLeft(2, '0');
                           timeText = '$hour:$minute $ampm';
                        } catch (e) {
                           timeText = '';
                        }
                      }

                      // Read status (mock for now if Odoo doesn't provide read receipts)
                      final bool isRead = true; // Could map to some Odoo field later

                      return Align(
                        alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          constraints: BoxConstraints(
                            maxWidth: MediaQuery.of(context).size.width * 0.75,
                          ),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            color: isMe ? const Color(0xFFDCF8C6) : Colors.white, // WhatsApp green/blue style for sender
                            borderRadius: BorderRadius.only(
                              topLeft: const Radius.circular(12),
                              topRight: const Radius.circular(12),
                              bottomLeft: isMe ? const Radius.circular(12) : const Radius.circular(0),
                              bottomRight: isMe ? const Radius.circular(0) : const Radius.circular(12),
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.1),
                                blurRadius: 2,
                                offset: const Offset(0, 1),
                              ),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                bodyText,
                                style: const TextStyle(fontSize: 15, color: Colors.black87),
                              ),
                              if (message['attachment_ids'] != null && (message['attachment_ids'] as List).isNotEmpty)
                                ...((message['attachment_ids'] as List).map((id) => AttachmentView(attachmentId: id as int)).toList()),
                              const SizedBox(height: 2),
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  Text(
                                    timeText, 
                                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                  ),
                                  if (isMe) ...[
                                    const SizedBox(width: 4),
                                    Icon(
                                      isRead ? Icons.done_all : Icons.done, 
                                      size: 14, 
                                      color: isRead ? Colors.blue : Colors.grey
                                    ),
                                  ]
                                ],
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
             if (_isUploading)
               const Padding(
                 padding: EdgeInsets.all(8.0),
                 child: CircularProgressIndicator(color: Color(0xFF1976D2)),
               ),
             if (_pendingFile != null)
               Container(
                 margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                 padding: const EdgeInsets.all(12),
                 decoration: BoxDecoration(
                   color: Colors.white,
                   borderRadius: BorderRadius.circular(12),
                   boxShadow: [
                     BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 4),
                   ],
                 ),
                 child: Row(
                   children: [
                     Icon(
                       _pendingFile!.extension?.toLowerCase() == 'jpg' || 
                       _pendingFile!.extension?.toLowerCase() == 'png' || 
                       _pendingFile!.extension?.toLowerCase() == 'jpeg' 
                           ? Icons.image : Icons.insert_drive_file,
                       color: Colors.blue,
                       size: 32,
                     ),
                     const SizedBox(width: 12),
                     Expanded(
                       child: Column(
                         crossAxisAlignment: CrossAxisAlignment.start,
                         children: [
                           Text(
                             _pendingFile!.name,
                             style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                             maxLines: 1,
                             overflow: TextOverflow.ellipsis,
                           ),
                           Text(
                             '${(_pendingFile!.size / 1024).toStringAsFixed(1)} KB',
                             style: const TextStyle(color: Colors.grey, fontSize: 12),
                           ),
                         ],
                       ),
                     ),
                     IconButton(
                       icon: const Icon(Icons.close, color: Colors.grey),
                       onPressed: () {
                         setState(() {
                           _pendingFile = null;
                         });
                       },
                     ),
                   ],
                 ),
               ),
             Container(
               padding: const EdgeInsets.all(8),
               color: Colors.transparent,
               child: Row(
                children: [
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: Row(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.add, color: Colors.grey),
                            onPressed: _showTemplates,
                          ),
                          Expanded(
                            child: TextField(
                              controller: _messageController,
                              decoration: const InputDecoration(
                                hintText: 'Message',
                                border: InputBorder.none,
                              ),
                              onSubmitted: (_) => _sendMessage(),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.attach_file, color: Colors.grey),
                            onPressed: _pickFile,
                          ),
                          IconButton(
                            icon: const Icon(Icons.camera_alt, color: Colors.grey),
                            onPressed: _pickImage,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: const Color(0xFF1976D2),
                    child: IconButton(
                      icon: const Icon(Icons.send, color: Colors.white),
                      onPressed: _sendMessage,
                    ),
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

class _TemplatesSheet extends StatefulWidget {
  final Function(Map<String, dynamic>) onTemplateSelected;

  const _TemplatesSheet({required this.onTemplateSelected});

  @override
  State<_TemplatesSheet> createState() => _TemplatesSheetState();
}

class _TemplatesSheetState extends State<_TemplatesSheet> {
  late Future<List<dynamic>> _templatesFuture;

  @override
  void initState() {
    super.initState();
    _templatesFuture = Provider.of<OdooApi>(context, listen: false).fetchTemplates();
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.6,
      maxChildSize: 0.9,
      minChildSize: 0.4,
      builder: (_, scrollController) => Container(
        padding: const EdgeInsets.only(top: 16),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const Text(
              'WhatsApp Templates',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const Divider(),
            Expanded(
              child: FutureBuilder<List<dynamic>>(
                future: _templatesFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  } else if (snapshot.hasError) {
                    return Center(child: Text('Error loading templates: ${snapshot.error}'));
                  } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return const Center(child: Text('No templates found.'));
                  } else {
                    final templates = snapshot.data!;
                    return ListView.separated(
                      controller: scrollController,
                      padding: const EdgeInsets.all(16),
                      itemCount: templates.length,
                      separatorBuilder: (_, __) => const Divider(),
                      itemBuilder: (context, index) {
                        final template = templates[index] as Map<String, dynamic>;
                        final name = template['template_name'] as String? ?? 'Unnamed';
                        final body = template['body'] as String? ?? '';
                        return ListTile(
                          title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text(body, maxLines: 2, overflow: TextOverflow.ellipsis),
                          onTap: () => widget.onTemplateSelected(template),
                        );
                      },
                    );
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class AttachmentView extends StatefulWidget {
  final int attachmentId;
  const AttachmentView({super.key, required this.attachmentId});

  @override
  State<AttachmentView> createState() => _AttachmentViewState();
}

class _AttachmentViewState extends State<AttachmentView> {
  String? _base64Data;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAttachment();
  }

  void _loadAttachment() async {
    final api = Provider.of<OdooApi>(context, listen: false);
    final data = await api.fetchAttachmentBase64(widget.attachmentId);
    if (mounted) {
      setState(() {
        _base64Data = data;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.only(top: 8.0),
        child: SizedBox(
          width: 20, 
          height: 20, 
          child: CircularProgressIndicator(strokeWidth: 2)
        ),
      );
    }
    
    if (_base64Data == null) {
      return const Padding(
        padding: EdgeInsets.only(top: 8.0),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.attachment, size: 16, color: Colors.grey),
            SizedBox(width: 4),
            Text('Attachment unavailable', style: TextStyle(color: Colors.grey, fontSize: 12)),
          ],
        ),
      );
    }

    try {
      final bytes = base64Decode(_base64Data!);
      return Container(
        margin: const EdgeInsets.only(top: 8.0),
        constraints: const BoxConstraints(maxHeight: 200),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8.0),
          child: Image.memory(
            bytes,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) {
              return Container(
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.insert_drive_file, color: Colors.grey),
                    SizedBox(width: 4),
                    Text('File Attached', style: TextStyle(color: Colors.black54)),
                  ],
                ),
              );
            },
          ),
        ),
      );
    } catch (e) {
       return const Padding(
        padding: EdgeInsets.only(top: 8.0),
        child: Icon(Icons.broken_image, color: Colors.grey),
      );
    }
  }
}

class _CatalogueSheet extends StatefulWidget {
  final Function(Map<String, dynamic>) onProductSelected;

  const _CatalogueSheet({required this.onProductSelected});

  @override
  State<_CatalogueSheet> createState() => _CatalogueSheetState();
}

class _CatalogueSheetState extends State<_CatalogueSheet> {
  late Future<List<dynamic>> _productsFuture;

  @override
  void initState() {
    super.initState();
    _productsFuture = Provider.of<OdooApi>(context, listen: false).fetchProducts();
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.8,
      maxChildSize: 0.9,
      minChildSize: 0.5,
      expand: false,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: const BoxDecoration(
                  color: Color(0xFF008069),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                ),
                child: Row(
                  children: [
                    const Expanded(
                      child: Text('Product Catalogue', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, color: Colors.white),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: FutureBuilder<List<dynamic>>(
                  future: _productsFuture,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return const Center(child: Text('Error loading products'));
                    }
                    final products = snapshot.data ?? [];
                    if (products.isEmpty) {
                      return const Center(child: Text('No products available.'));
                    }
                    return GridView.builder(
                      controller: scrollController,
                      padding: const EdgeInsets.all(16),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        childAspectRatio: 0.75,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                      ),
                      itemCount: products.length,
                      itemBuilder: (context, index) {
                        final product = products[index] as Map<String, dynamic>;
                        final imageBase64 = product['image_128'] as String?;
                        
                        return GestureDetector(
                          onTap: () => widget.onProductSelected(product),
                          child: Card(
                            elevation: 2,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Expanded(
                                  child: imageBase64 != null
                                      ? Image.memory(base64Decode(imageBase64), fit: BoxFit.cover)
                                      : Container(color: Colors.grey.shade200, child: const Icon(Icons.image, size: 50, color: Colors.grey)),
                                ),
                                Padding(
                                  padding: const EdgeInsets.all(8.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(product['name']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.bold), maxLines: 1, overflow: TextOverflow.ellipsis),
                                      if (product['list_price'] != null)
                                        Text('\$${product['list_price']}', style: const TextStyle(color: Color(0xFF008069), fontWeight: FontWeight.bold)),
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
}
