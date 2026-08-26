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
# section5
sec5=[]
for n in ['c4b_1.rpy','c4b_2.rpy','c4b_3.rpy','c4b_4.rpy','c4b_5.rpy']:
    sec5 += lines(out/n)
assert len(sec5)==2347, len(sec5)
(root/'sections'/'trans_sec5.rpy').write_text('\n'.join(sec5)+'\n', encoding='utf-8', newline='\n')
for idx,(start,end) in enumerate([(0,550),(550,1100),(1100,1650),(1650,2200),(2200,2347)],24):
    part=sec5[start:end]
    (slices/f'trans_sl{idx:02d}.rpy').write_text('\n'.join(part)+'\n', encoding='utf-8', newline='\n')
    print(f'trans_sl{idx:02d}', len(part), repr(part[0][:80]), repr(part[-1][:80]))
# section6
sec6=[]
for n in ['c4c_1.rpy','c4c_2.rpy','c4c_3.rpy']:
    sec6 += lines(out/n)
assert len(sec6)==1401, len(sec6)
(root/'sections'/'trans_sec6.rpy').write_text('\n'.join(sec6)+'\n', encoding='utf-8', newline='\n')
for idx,(start,end) in enumerate([(0,550),(550,1100),(1100,1401)],29):
    part=sec6[start:end]
    (slices/f'trans_sl{idx:02d}.rpy').write_text('\n'.join(part)+'\n', encoding='utf-8', newline='\n')
    print(f'trans_sl{idx:02d}', len(part), repr(part[0][:80]), repr(part[-1][:80]))
print('trans_sec5', len(sec5), 'trans_sec6', len(sec6))
