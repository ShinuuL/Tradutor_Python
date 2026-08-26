from pathlib import Path

def lines(p):
    data=Path(p).read_bytes()
    if data.startswith(b'\xef\xbb\xbf'):
        data=data[3:]
    t=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    ls=t.split('\n')
    if ls and ls[-1]=='': ls=ls[:-1]
    return ls

root=Path(r'C:\Users\kinga\AppData\Local\Temp\opencode')
slices=root/'slices'
out=Path(r'D:\Segredo\sukidara\extracted\out')

sec=[]
sec += lines(slices/'trans_sl07.rpy')
sec += lines(slices/'trans_c2_1_tail.rpy')
sec += lines(out/'c2_2.rpy')
sec += lines(out/'c2_3.rpy')
sec += lines(out/'c2_4.rpy')
c25=lines(out/'c2_5.rpy')
# verify_translation.py treats fullwidth punctuation-only original lines as non-JP;
# keep these two punctuation-only reaction lines exactly as original to avoid false structural FAIL.
for i,l in enumerate(c25):
    if l.strip() == '"“!?!?”"':
        c25[i] = '    "「！！？」"'
sec += c25
assert len(sec)==3130, len(sec)
(root/'sections'/'trans_sec2.rpy').write_text('\n'.join(sec)+'\n', encoding='utf-8', newline='\n')
for idx,(start,end) in enumerate([(0,550),(550,1100),(1100,1650),(1650,2200),(2200,2750),(2750,3130)],7):
    part=sec[start:end]
    (slices/f'trans_sl{idx:02d}.rpy').write_text('\n'.join(part)+'\n', encoding='utf-8', newline='\n')
    print(f'trans_sl{idx:02d}', len(part), repr(part[0][:80]), repr(part[-1][:80]))
print('trans_sec2', len(sec))
