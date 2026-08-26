import os

def lines(p):
    data=open(p,'rb').read()
    if data.startswith(b'\xef\xbb\xbf'):
        data=data[3:]
    t=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    ls=t.split('\n')
    if ls and ls[-1]=='':
        ls=ls[:-1]
    return ls

base=r'D:\Segredo\sukidara\extracted'
sections=[]
for i in range(1,7):
    sections.append(lines(rf'C:\Users\kinga\AppData\Local\Temp\opencode\sections\orig_sec{i}.rpy'))

names=['c2_2.rpy','c2_3.rpy','c2_4.rpy','c2_5.rpy','c3_b.rpy','c3_c.rpy','c3_d.rpy','c4a_1.rpy','c4a_3.rpy','c4a_4.rpy','c4a_5.rpy','c4a_6.rpy','c4b_1.rpy','c4b_2.rpy','c4b_3.rpy','c4b_4.rpy','c4b_5.rpy','c4c_1.rpy','c4c_2.rpy','c4c_3.rpy']
for name in names:
    out=lines(os.path.join(base,'out',name))
    first=out[0]
    hits=[]
    for si,sec in enumerate(sections,1):
        for idx,line in enumerate(sec):
            if line==first:
                hits.append((si,idx+1))
    print(name, 'len', len(out), 'hits', hits)
