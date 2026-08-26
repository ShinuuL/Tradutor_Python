import os

def readlines(p):
    data = open(p, 'rb').read()
    if data.startswith(b'\xef\xbb\xbf'):
        data = data[3:]
    t = data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    ls = t.split('\n')
    if ls and ls[-1] == '':
        ls = ls[:-1]
    return ls

SIZES = [3276, 3130, 3054, 2695, 2347, 1401]
root = readlines(r'D:\Segredo\sukidara\extracted\script.rpy')
assert sum(SIZES) == len(root), (sum(SIZES), len(root))

outdir = r'C:\Users\kinga\AppData\Local\Temp\opencode\sections'
os.makedirs(outdir, exist_ok=True)

# full snapshot for final verification
with open(os.path.join(outdir, 'script_orig_full.rpy'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(root) + '\n')

pos = 0
for i, n in enumerate(SIZES, 1):
    sec = root[pos:pos + n]
    pos += n
    p = os.path.join(outdir, f'orig_sec{i}.rpy')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(sec) + '\n')
    print(f'orig_sec{i}.rpy: {len(sec)} lines  first={sec[0][:70]!r}  last={sec[-1][:70]!r}')
