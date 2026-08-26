import os, re

JP=re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
def lines(p):
    data=open(p,'rb').read()
    if data.startswith(b'\xef\xbb\xbf'):
        data=data[3:]
    t=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    ls=t.split('\n')
    if ls and ls[-1]=='':
        ls=ls[:-1]
    return ls

def score(orig, trans):
    if len(orig)!=len(trans): return None
    changed_nonjp=0
    for o,t in zip(orig,trans):
        if not JP.search(o) and o!=t:
            changed_nonjp += 1
            if changed_nonjp>0:
                return changed_nonjp
    return 0

base=r'D:\Segredo\sukidara\extracted'
sections={i:lines(rf'C:\Users\kinga\AppData\Local\Temp\opencode\sections\orig_sec{i}.rpy') for i in range(1,7)}
names=['c2_2.rpy','c2_3.rpy','c2_4.rpy','c2_5.rpy','c3_b.rpy','c3_c.rpy','c3_d.rpy','c4a_1.rpy','c4a_3.rpy','c4a_4.rpy','c4a_5.rpy','c4a_6.rpy','c4b_1.rpy','c4b_2.rpy','c4b_3.rpy','c4b_4.rpy','c4b_5.rpy','c4c_1.rpy','c4c_2.rpy','c4c_3.rpy']
for name in names:
    trans=lines(os.path.join(base,'out',name))
    good=[]
    best=[]
    for si,sec in sections.items():
        for start in range(0, len(sec)-len(trans)+1):
            s=score(sec[start:start+len(trans)], trans)
            if s==0:
                good.append((si,start+1,start+len(trans)))
    print(name, len(trans), 'GOOD', good[:10], 'count', len(good))
