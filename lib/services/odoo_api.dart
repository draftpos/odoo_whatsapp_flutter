import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'http_client_native.dart'
    if (dart.library.html) 'http_client_web.dart';


class OdooApi with ChangeNotifier {
  String? _baseUrl;
  String? _db;
  String? _password;
  int? _uid;
  int? _partnerId; // partner linked to the logged-in user
  bool _isLead = false; // Is the logged-in user a lead?

  bool get isLoggedIn => _uid != null && _password != null;
  String? get baseUrl => _baseUrl;
  String? get db => _db;
  int? get uid => _uid;
  int? get partnerId => _partnerId;
  bool get isLead => _isLead;

  Map<String, String> get _headers => {'Content-Type': 'application/json'};

  Future<List<String>> fetchDatabases(String url) async {
    final cleanUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    final requestUrl = Uri.parse('$cleanUrl/jsonrpc');
    final body = {
      'jsonrpc': '2.0',
      'method': 'call',
      'params': {
        'service': 'db',
        'method': 'list',
        'args': []
      },
      'id': DateTime.now().millisecondsSinceEpoch,
    };

    try {
      final client = createHttpClient();
      try {
        final response = await client.post(
          requestUrl,
          headers: {'Content-Type': 'application/json'},
          body: json.encode(body),
        );
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          if (data['result'] is List) {
            return List<String>.from(data['result']);
          }
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('fetchDatabases error: $e');
    }
    return [];
  }

  // ─── Auth ─────────────────────────────────────────────────────────────────

  Future<bool> login(String url, String db, String username, String password) async {
    _baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
    _db = db;
    _password = password;

    final requestUrl = Uri.parse('$_baseUrl/jsonrpc');
    final body = {
      'jsonrpc': '2.0',
      'method': 'call',
      'params': {
        'service': 'common',
        'method': 'authenticate',
        'args': [
          _db,
          username,
          password,
          {},
        ]
      },
      'id': DateTime.now().millisecondsSinceEpoch,
    };

    try {
      final client = createHttpClient();
      try {
        final response = await client.post(
          requestUrl,
          headers: _headers,
          body: json.encode(body),
        );
        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          debugPrint('JSONRPC Authenticate Response: $data');
          if (data.containsKey('result') && data['result'] != null && data['result'] is int) {
            _uid = data['result'];
            debugPrint('JSONRPC Authenticate SUCCESS: UID = $_uid');

            final prefs = await SharedPreferences.getInstance();
            await prefs.setString('odoo_url', _baseUrl!);
            await prefs.setString('odoo_db', _db!);
            await prefs.setString('odoo_username', username);
            await prefs.setString('odoo_password', password); // Store securely in production
            await prefs.setInt('odoo_uid', _uid!);

            // Fetch partner ID
            await fetchCurrentUserProfile();

            notifyListeners();
            return true;
          } else {
             debugPrint('JSONRPC Authenticate FAILED: result is not an int or missing. Result: ${data['result']}');
          }
        } else {
             debugPrint('JSONRPC Authenticate HTTP ERROR: ${response.statusCode}');
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Login Error: $e');
    }
    return false;
  }


  Future<void> logout() async {
    _uid = null;
    _password = null;
    _partnerId = null;
    _isLead = false;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('odoo_password');
    await prefs.remove('odoo_uid');
    notifyListeners();
  }

  // ─── Generic RPC ──────────────────────────────────────────────────────────

  Future<dynamic> _callKw({
    required String model,
    required String method,
    List<dynamic> args = const [],
    Map<String, dynamic> kwargs = const {},
  }) async {
    if (_uid == null) return null;

    final requestUrl = Uri.parse('$_baseUrl/jsonrpc');
    final body = {
      'jsonrpc': '2.0',
      'method': 'call',
      'params': {
        'service': 'object',
        'method': 'execute_kw',
        'args': [_db, _uid, _password, model, method, args, kwargs],
      },
      'id': DateTime.now().millisecondsSinceEpoch,
    };

    try {
      final client = createHttpClient();
      try {
        final response = await client.post(
          requestUrl,
          headers: _headers,
          body: json.encode(body),
        );

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          if (data.containsKey('result')) {
            return data['result'];
          } else if (data.containsKey('error')) {
            debugPrint('Odoo RPC Error: ${data['error']}');
          }
        } else {
          debugPrint('HTTP Error: ${response.statusCode} - ${response.body}');
        }

      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('_callKw Error [$model.$method]: $e');
    }
    return null;
  }

  /// search_read via call_kw (Odoo 17+)
  Future<List<dynamic>> searchRead(
    String model,
    List<dynamic> domain,
    List<String> fields, {
    int limit = 80,
    String order = 'id desc',
  }) async {
    final result = await _callKw(
      model: model,
      method: 'search_read',
      args: [domain],
      kwargs: {'fields': fields, 'limit': limit, 'order': order},
    );
    if (result is List) return result;
    return [];
  }

  // ─── User / Profile ───────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> fetchCurrentUserProfile() async {
    if (!isLoggedIn || _uid == null) return null;
    final records = await searchRead(
      'res.partner',
      [['user_ids', 'in', [_uid]]],
      ['id', 'name', 'phone', 'is_lead'],
      limit: 1,
    );
    if (records.isNotEmpty) {
      final p = records[0] as Map<String, dynamic>;
      _partnerId = p['id'];
      _isLead = p['is_lead'] == true;
      return p;
    }
    return null;
  }

  Future<Map<String, dynamic>?> fetchAdminPartner() async {
    try {
      // First try to fetch the company partner, which is usually public/accessible
      final companies = await searchRead(
        'res.company',
        [],
        ['partner_id'],
        limit: 1,
      );
      
      int? targetPartnerId;
      if (companies.isNotEmpty && companies[0]['partner_id'] != null) {
        targetPartnerId = companies[0]['partner_id'][0];
      } else {
        // Fallback to user id 2
        final users = await searchRead(
          'res.users',
          [['id', '=', 2]],
          ['partner_id'],
          limit: 1,
        );
        if (users.isNotEmpty && users[0]['partner_id'] != null) {
          targetPartnerId = users[0]['partner_id'][0];
        }
      }

      if (targetPartnerId != null) {
        final partners = await searchRead(
          'res.partner',
          [['id', '=', targetPartnerId]],
          ['id', 'name', 'phone', 'email'],
        );
        if (partners.isNotEmpty) {
          return partners[0] as Map<String, dynamic>;
        }
      }
    } catch (e) {
      debugPrint('fetchAdminPartner error: $e');
    }
    return null;
  }

  Future<String?> fetchBusinessWhatsAppNumber() async {
    try {
      // First, attempt to read standard and potential fields from whatsapp.account
      final accounts = await searchRead(
        'whatsapp.account',
        [], // get any active account
        ['name'], // Only query name to avoid Odoo Server Errors for non-existent fields
        limit: 1,
      );
      
      if (accounts.isNotEmpty) {
        final acc = accounts[0];
        
        // Fallback: If they named the account with their phone number (e.g. "+123456789")
        final name = acc['name']?.toString() ?? '';
        final cleanName = name.replaceAll(RegExp(r'[^\d]'), '');
        if (cleanName.length >= 8) {
          return cleanName;
        }
      }
    } catch (e) {
      debugPrint('fetchBusinessWhatsAppNumber error: $e');
    }
    return null;
  }

  // ─── Contacts ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchContacts() async {
    // Use empty domain to fetch ALL partners — no filter at all.
    // Avoids the type/active field issues that silently hide records.
    debugPrint('fetchContacts: Fetching contacts from Odoo...');
    final result = await searchRead(
      'res.partner',
      [], // domain is empty initially
      ['id', 'name', 'phone', 'email', 'is_company', 'is_lead'],
      order: 'name asc',
      limit: 200,
    );
    
    debugPrint('fetchContacts: Received ${result.length} contacts.');
    if (result.isEmpty) {
       debugPrint('fetchContacts: Result is empty. Check session and permissions.');
       return [];
    }
    
    // Filtering logic based on is_lead status
    if (_isLead) {
      // If the current user is a lead, they should ONLY see the admin
      try {
        final admin = await fetchAdminPartner();
        if (admin != null) {
          return [admin];
        }
      } catch (e) {
        debugPrint('fetchContacts error filtering for lead: $e');
      }
      return [];
    }

    return result;
  }


  // ─── Accounts ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchAccounts() async {
    try {
      return await searchRead(
        'whatsapp.account',
        [],
        ['id', 'name', 'image_1920'],
      );
    } catch (e) {
      debugPrint('Error fetching accounts: $e');
      return [];
    }
  }

  // ─── Chats / Channels ─────────────────────────────────────────────────────

  /// Fetches ALL discuss.channel records the current user has access to.
  /// Includes WhatsApp channels (channel_type='whatsapp') as well as DMs and groups.
  Future<List<dynamic>> fetchChats({int? accountId}) async {
    final domain = <dynamic>[];
    if (accountId != null) {
      domain.add(['wa_account_id', '=', accountId]);
    }

    // Fetch WhatsApp channels via custom method (bypasses record rules)
    final waResult = await _callKw(
      model: 'whatsapp.account',
      method: 'get_whatsapp_web_channels',
      args: [],
      kwargs: accountId != null ? {'wa_account_id': accountId} : {},
    );
    final waChannels = (waResult is List) ? List<dynamic>.from(waResult) : [];

    // Fetch non-whatsapp channels via standard searchRead
    final otherDomain = List<dynamic>.from(domain)..add(['channel_type', '!=', 'whatsapp']);
    final otherChannels = await searchRead(
      'discuss.channel',
      otherDomain,
      [
        'id', 'name', 'channel_type', 'message_needaction_counter',
        'write_date', 'whatsapp_number', 'whatsapp_partner_id', 'wa_account_id',
      ],
      order: 'write_date desc',
    );
    
    final channels = [...waChannels, ...otherChannels];

    final partnerIds = <int>{};
    for (var c in channels) {
      if (c['whatsapp_partner_id'] != null && c['whatsapp_partner_id'] is List && c['whatsapp_partner_id'].isNotEmpty) {
        partnerIds.add(c['whatsapp_partner_id'][0] as int);
      }
    }
    
    if (partnerIds.isNotEmpty) {
      final partners = await searchRead('res.partner', [['id', 'in', partnerIds.toList()]], ['id', 'avatar_128', 'phone']);
      final partnerMap = <int, Map<String, dynamic>>{};
      for (var p in partners) {
        final avatar = p['avatar_128'];
        final phone = (p['phone'] is String ? p['phone'] : null);
            
        partnerMap[p['id'] as int] = {
          'image': (avatar is bool) ? null : avatar as String?,
          'phone': phone,
        };
      }
      for (var c in channels) {
        if (c['whatsapp_partner_id'] != null && c['whatsapp_partner_id'] is List && c['whatsapp_partner_id'].isNotEmpty) {
          final pData = partnerMap[c['whatsapp_partner_id'][0] as int];
          if (pData != null) {
            c['customer_image'] = pData['image'];
            c['customer_phone'] = pData['phone'];
          }
        }
      }
    }
    
    return channels;
  }

  // ─── Products / Catalogue ──────────────────────────────────────────────────

  Future<List<dynamic>> fetchProducts() async {
    return await searchRead(
      'product.product',
      [['sale_ok', '=', true], ['show_in_catalogue', '=', true]],
      ['id', 'name', 'list_price', 'image_128'],
    );
  }

  // ─── Templates ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchTemplates() async {
    try {
      return await searchRead(
        'whatsapp.template',
        [],
        ['id', 'template_name', 'body'],
      );
    } catch (e) {
      print('Error fetching templates: $e');
      return [];
    }
  }

  // ─── Messages ─────────────────────────────────────────────────────────────

  Future<List<dynamic>> fetchMessages(int channelId) async {
    final result = await _callKw(
      model: 'whatsapp.account',
      method: 'get_whatsapp_web_messages',
      args: [channelId],
      kwargs: {},
    );
    return (result is List) ? List<dynamic>.from(result) : [];
  }

  Future<void> markChannelAsRead(int channelId) async {
    try {
      await _callKw(
        model: 'whatsapp.account',
        method: 'mark_whatsapp_web_messages_read',
        args: [channelId],
        kwargs: {},
      );
    } catch (e) {
      debugPrint('Error marking channel as read: $e');
    }
  }

  /// Sends a message via discuss.channel.message_post (correct Odoo 17 API).
  Future<bool> sendMessage(int channelId, String text,
      {List<int>? attachmentIds, bool isWhatsapp = false}) async {
    final kwargs = <String, dynamic>{
      'body': text,
      'message_type': isWhatsapp ? 'whatsapp_message' : 'comment',
      'subtype_xmlid': 'mail.mt_comment',
    };
    if (attachmentIds != null && attachmentIds.isNotEmpty) {
      kwargs['attachment_ids'] = attachmentIds;
    }

    final result = await _callKw(
      model: 'discuss.channel',
      method: 'message_post',
      args: [channelId],
      kwargs: kwargs,
    );
    return result != null;
  }

  // ─── Direct chat ──────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> getOrCreateDirectChat(int partnerIdVal) async {
    if (_partnerId == null) return null;

    // 1. Try to find the existing chat. 
    // Due to Odoo record rules, this will only return channels the current user is a member of.
    try {
      final existingChannels = await searchRead(
        'discuss.channel',
        [
          ['channel_type', '=', 'chat'],
          ['channel_member_ids.partner_id', 'in', [partnerIdVal]],
        ],
        ['id', 'name', 'channel_type'],
        limit: 1,
      );

      if (existingChannels.isNotEmpty) {
        return Map<String, dynamic>.from(existingChannels[0]);
      }
    } catch (e) {
      debugPrint('searchRead for existing chat failed: $e');
    }

    // 2. If it doesn't exist, try to create it.
    try {
      final result = await _callKw(
        model: 'discuss.channel',
        method: 'create',
        args: [
          {
            'name': 'Direct Message',
            'channel_type': 'chat',
            'channel_member_ids': [
              [0, 0, {'partner_id': partnerIdVal}],
            ],
          }
        ],
      );

      int? channelId;
      if (result is int) {
        channelId = result;
      } else if (result is List && result.isNotEmpty && result[0] is int) {
        channelId = result[0];
      }

      if (channelId != null) {
        final channels = await searchRead(
          'discuss.channel',
          [['id', '=', channelId]],
          ['id', 'name', 'channel_type'],
        );
        if (channels.isNotEmpty) return channels[0] as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('create chat failed: $e');
    }

    return null;
  }

  // ─── Attachments ──────────────────────────────────────────────────────────

  Future<int?> uploadAttachment(String filename, String base64Data) async {
    final result = await _callKw(
      model: 'ir.attachment',
      method: 'create',
      args: [
        {
          'name': filename,
          'datas': base64Data,
          'res_model': 'discuss.channel',
        }
      ],
    );
    if (result is int) return result;
    return null;
  }

  Future<String?> fetchAttachmentBase64(int attachmentId) async {
    final result = await searchRead(
      'ir.attachment',
      [['id', '=', attachmentId]],
      ['id', 'datas'],
      limit: 1,
    );
    if (result.isNotEmpty && result[0]['datas'] != null) {
      // For Odoo 15+, 'datas' might be returned as bytes but over JSONRPC it's base64 string
      return result[0]['datas'] as String;
    }
    return null;
  }

  // ─── Call contacts ────────────────────────────────────────────────────────

  /// Partners that have a phone or mobile number, for the Calls tab.
  Future<List<dynamic>> fetchCallContacts() async {
    return await searchRead(
      'res.partner',
      [
        ['active', '=', true],
        '|',
        ['phone', '!=', false],
      ],
      ['id', 'name', 'phone'],
      order: 'name asc',
      limit: 100,
    );
  }
}

