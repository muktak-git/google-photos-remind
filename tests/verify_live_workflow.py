import urllib.request
import json

def post(path, body):
    req = urllib.request.Request(
        'http://127.0.0.1:8000' + path,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

s = post('/api/search', {'query': 'That cafe in coorg.'})['session_id']
c1 = post('/api/candidates', {'session_id': s})
print('--- Turn 1 (Initial Search) ---')
print('Banner:', c1['banner_message'])

c2 = post('/api/candidates', {'session_id': s, 'constraint': {'dimension': 'visual', 'value': 'Blue wall'}})
print('\n--- Turn 2 (Blue wall match) ---')
print('Total photos:', c2['total'])
print('Banner:', c2['banner_message'])
print('Prompt:', c2['refinement']['follow_up_prompt'])
print('Options:', c2['refinement']['options'])

c3 = post('/api/candidates', {'session_id': s, 'constraint': {'dimension': 'recognition', 'value': 'No'}})
print('\n--- Turn 3 (User clicks No) ---')
print('Banner:', c3['banner_message'])
print('Prompt:', c3['refinement']['follow_up_prompt'])
print('Dimension:', c3['refinement']['dimension'])
print('Smart Hint Keywords (from input embeddings):', c3['refinement']['hint_keywords'])
