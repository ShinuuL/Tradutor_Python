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

outdir = r'C:\Users\kinga\AppData\Local\Temp\opencode\slices'
os.makedirs(outdir, exist_ok=True)
SIZE = 550
idx = 0
for sec in range(1, 7):
    src = rf'C:\Users\kinga\AppData\Local\Temp\opencode\sections\orig_sec{sec}.rpy'
    ls = readlines(src)
    for start in range(0, len(ls), SIZE):
        idx += 1
        part = ls[start:start + SIZE]
        p = os.path.join(outdir, f'orig_sl{idx:02d}.rpy')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(part) + '\n')
        print(f'orig_sl{idx:02d}.rpy  sec{sec}  lines {start+1}-{start+len(part)} ({len(part)})')
