from pathlib import Path

def lines(p):
    data=Path(p).read_bytes()
    if data.startswith(b'\xef\xbb\xbf'): data=data[3:]
    t=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    ls=t.split('\n')
    if ls and ls[-1]=='': ls=ls[:-1]
    return ls

root=Path(r'C:\Users\kinga\AppData\Local\Temp\opencode')
slices=root/'slices'
out=Path(r'D:\Segredo\sukidara\extracted\out')
sec=[]
sec += lines(slices/'trans_c3a_1.rpy')
sec += lines(slices/'trans_c3a_2.rpy')
sec += lines(out/'c3_b.rpy')
sec += lines(out/'c3_c.rpy')
sec += lines(out/'c3_d.rpy')
assert len(sec)==3054, len(sec)
(root/'sections'/'trans_sec3.rpy').write_text('\n'.join(sec)+'\n', encoding='utf-8', newline='\n')
bounds=[(0,550),(550,1100),(1100,1650),(1650,2200),(2200,2750),(2750,3054)]
for idx,(start,end) in enumerate(bounds,13):
    part=sec[start:end]
    (slices/f'trans_sl{idx:02d}.rpy').write_text('\n'.join(part)+'\n', encoding='utf-8', newline='\n')
    print(f'trans_sl{idx:02d}', len(part), repr(part[0][:80]), repr(part[-1][:80]))
print('trans_sec3', len(sec))
