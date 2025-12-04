import requests

pdf_path = r"C:\Users\jmyang\Downloads\나경원.pdf"

with open(pdf_path, 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/convert',
        files={'file': ('나경원.pdf', f, 'application/pdf')},
        data={'content_type': 'election'}
    )
    result = response.json()
    print(f"Status: {result.get('status')}")
    print(f"Job ID: {result.get('job_id')}")
    print(f"URL: {result.get('url')}")
    if result.get('error'):
        print(f"Error: {result.get('error')}")
