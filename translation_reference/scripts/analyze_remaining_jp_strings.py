import re
from pathlib import Path
JP=re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
SFX_HINT=re.compile(r'^[\s…\.！!？?♡♥ー〜～、。・「」『』（）()\u3040-\u30ff\u30a0-\u30ff]+$')

def lines(p):
    data=Path(p).read_bytes()
    if data.startswith(b'\xef\xbb\xbf'): data=data[3:]
    t=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    ls=t.split('\n')
    if ls and ls[-1]=='': ls=ls[:-1]
    return ls

def strings_in_line(line):
    out=[]; i=0
    while i < len(line):
        q=line.find('"', i)
        sq=line.find("'", i)
        choices=[x for x in [q,sq] if x!=-1]
        if not choices: break
        start=min(choices); quote=line[start]; j=start+1; esc=False
        buf=[]
        while j < len(line):
            c=line[j]
            if esc:
                buf.append(c); esc=False
            elif c=='\\':
                buf.append(c); esc=True
            elif c==quote:
                out.append(''.join(buf)); break
            else:
                buf.append(c)
            j+=1
        i=j+1
    return out

allowed_exact={'月','火','水','木','金','土','日','危険'}
rows=[]
for n,line in enumerate(lines(r'D:\Segredo\sukidara\extracted\script.rpy'),1):
    if line.lstrip().startswith('#'):
        continue
    for s in strings_in_line(line):
        if not JP.search(s):
            continue
        if s in allowed_exact:
            continue
        rows.append((n,s,line[:180]))
print('JP strings remaining:', len(rows))
for n,s,l in rows[:200]:
    print(f'{n}: {s!r} || {l}')
