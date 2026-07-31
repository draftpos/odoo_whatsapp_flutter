import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('remote_chatbot_processor.py', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Read the full _handle_single_message and everything around handed_off state
print("\n=== Lines 95-200 (entry + session search) ===")
print(''.join(lines[94:200]))

with open('remote_wa_chatbot_session.py', encoding='utf-8') as f:
    session_lines = f.readlines()

print(f"\n=== wa_chatbot_session.py FULL ({len(session_lines)} lines) ===")
# Look for expire cron logic
for i, line in enumerate(session_lines):
    lower = line.lower()
    if 'handed_off' in lower or 'expire' in lower or 'cron' in lower or 'resume' in lower:
        start = max(0, i-2)
        end = min(len(session_lines), i+10)
        print(f'[Line {i+1}]')
        print(''.join(session_lines[start:end]))
        print('...')
