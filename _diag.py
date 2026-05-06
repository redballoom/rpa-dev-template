import os

p = r'D:\CraftPJ\开发模板\run.bat'
with open(p, 'rb') as f:
    data = f.read()

print(f"Size: {len(data)}")
print(f"BOM (first 3 bytes): {data[:3].hex()}")
print(f"Encoding hint: {'UTF-8 BOM' if data[:3] == b'\xef\xbb\xbf' else 'No BOM'}")

# Find REPO_PATH line
idx = data.find(b'REPO_PATH')
if idx > 0:
    line_end = data.find(b'\n', idx)
    line = data[idx:line_end]
    print(f"REPO_PATH raw bytes: {line}")
    print(f"REPO_PATH hex: {line.hex(' ')}")
    try:
        print(f"REPO_PATH utf-8: {line.decode('utf-8')}")
    except:
        try:
            print(f"REPO_PATH gbk: {line.decode('gbk')}")
        except:
            print("Cannot decode REPO_PATH line")
