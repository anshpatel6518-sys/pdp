import os
import requests

logos = {
    'dp_logo.svg': 'https://api.dicebear.com/7.x/initials/svg?seed=DP&backgroundColor=0d6efd',
    'pa_logo.svg': 'https://api.dicebear.com/7.x/initials/svg?seed=PA&backgroundColor=198754',
    'nyf_logo.svg': 'https://api.dicebear.com/7.x/initials/svg?seed=NYF&backgroundColor=dc3545',
    'gfp_logo.svg': 'https://api.dicebear.com/7.x/initials/svg?seed=GFP&backgroundColor=ffc107',
    'pv_logo.svg': 'https://api.dicebear.com/7.x/initials/svg?seed=PV&backgroundColor=6f42c1',
}

os.makedirs('static/logos', exist_ok=True)

for filename, url in logos.items():
    print(f"Downloading {filename}...")
    response = requests.get(url)
    if response.status_code == 200:
        with open(os.path.join('static/logos', filename), 'wb') as f:
            f.write(response.content)
    else:
        print(f"Failed to download {filename}")

print("Done!")
