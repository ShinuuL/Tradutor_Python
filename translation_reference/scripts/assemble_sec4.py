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
sec += lines(out/'c4a_1.rpy')
sec += lines(slices/'trans_c4a_2.rpy')
sec += lines(out/'c4a_3.rpy')
sec += lines(out/'c4a_4.rpy')
sec += lines(out/'c4a_5.rpy')
sec += lines(out/'c4a_6.rpy')
assert len(sec)==2695, len(sec)
(root/'sections'/'trans_sec4.rpy').write_text('\n'.join(sec)+'\n', encoding='utf-8', newline='\n')
bounds=[(0,550),(550,1100),(1100,1650),(1650,2200),(2200,2695)]
for idx,(start,end) in enumerate(bounds,19):
    part=sec[start:end]
    (slices/f'trans_sl{idx:02d}.rpy').write_text('\n'.join(part)+'\n', encoding='utf-8', newline='\n')
    print(f'trans_sl{idx:02d}', len(part), repr(part[0][:80]), repr(part[-1][:80]))
print('trans_sec4', len(sec))
