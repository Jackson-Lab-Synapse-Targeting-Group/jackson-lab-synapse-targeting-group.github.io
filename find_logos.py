import urllib.request, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Find UKDRI logo - look for their site logo (not partner logos)
try:
    req = urllib.request.Request('https://ukdri.ac.uk', headers=headers)
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    # look for site-logo or header logo
    matches = re.findall(r'(?:site-logo|header)[^<]*<img[^>]*src=["\']([^"\'> ]+)["\']', html)
    print('UKDRI header logo: ' + str(matches[:3]))
    # also check for logo in title/header
    chunk = html[:5000]
    imgs = re.findall(r'src=["\']([^"\'> ]+)["\']', chunk)
    print('UKDRI first 5000 imgs: ' + str(imgs[:10]))
except Exception as e:
    print('UKDRI: ' + str(e))

# Imperial - check for SVG or PNG logo specifically
try:
    req = urllib.request.Request('https://www.imperial.ac.uk', headers=headers)
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    chunk = html[:5000]
    imgs = re.findall(r'src=["\']([^"\'> ]+)["\']', chunk)
    print('Imperial first imgs: ' + str(imgs[:10]))
    # look for svg logo
    svgs = re.findall(r'href=["\']([^"\'> ]+\.svg)["\']', html)
    print('Imperial SVGs: ' + str(svgs[:5]))
except Exception as e:
    print('Imperial: ' + str(e))

# BrightFocus - look for their own logo
try:
    req = urllib.request.Request('https://www.brightfocus.org', headers=headers)
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
    chunk = html[:5000]
    imgs = re.findall(r'src=["\']([^"\'> ]+)["\']', chunk)
    print('BrightFocus first imgs: ' + str(imgs[:10]))
except Exception as e:
    print('BrightFocus: ' + str(e))
