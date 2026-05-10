import jwt, json

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY4NTA2NDMwLCJpYXQiOjE3Njg0ODg0MzAsImp0aSI6ImU0YWQwODcxNzkyMDQ0YjM5NWU1YjUyODhhMzdmZTc2IiwidXNlcl9pZCI6IjU1In0.5seZfqJKb8Jp-PWP3zWM6Xdtg6iaD5Ri-2VKTamoKQY'

try:
    payload = jwt.decode(token, options={'verify_signature': False})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
except Exception as e:
    print('Error decoding token:', e)
