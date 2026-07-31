import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('remote_chatbot_processor.py', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in chatbot_processor.py: {len(lines)}")

# Find all functions and key logic around human handover
print("\n\n=== HUMAN / HANDOVER REFERENCES ===")
for i, line in enumerate(lines):
    lower = line.lower()
    if 'human' in lower or 'handover' in lower or 'hand_over' in lower or 'talk_to' in lower or 'human_agent' in lower:
        start = max(0, i-3)
        end = min(len(lines), i+8)
        print(f'--- LINE {i+1} ---')
        print(''.join(lines[start:end]))

print("\n\n=== SESSION EXPIRE / TIMEOUT / RESUME REFERENCES ===")
for i, line in enumerate(lines):
    lower = line.lower()
    if any(kw in lower for kw in ['expire', 'timeout', 'resume', 'reset', 'restart', 'reactivat', 'session_state', 'is_active', 'status']):
        start = max(0, i-2)
        end = min(len(lines), i+5)
        print(f'--- LINE {i+1} ---')
        print(''.join(lines[start:end]))
