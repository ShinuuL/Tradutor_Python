from pathlib import Path
def lines(p):
    data=Path(p).read_bytes()
    if data.startswith(b'\xef\xbb\xbf'):
        data=data[3:]
    t=data.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    ls=t.split('\n')
    if ls and ls[-1]=='':
        ls=ls[:-1]
    return ls
root=Path(r'C:\Users\kinga\AppData\Local\Temp\opencode')
sections=root/'sections'
all_lines=[]
for i in range(1,7):
    sec=lines(sections/f'trans_sec{i}.rpy')
    print(f'trans_sec{i}', len(sec), repr(sec[0][:80]), repr(sec[-1][:80]))
    all_lines += sec
assert len(all_lines)==15903, len(all_lines)
target=Path(r'D:\Segredo\sukidara\extracted\script.rpy')
backup=Path(r'C:\Users\kinga\AppData\Local\Temp\opencode\sections\script_before_final_assembly.rpy')
backup.write_bytes(target.read_bytes())
target.write_text('\r\n'.join(all_lines)+'\r\n', encoding='utf-8', newline='')
print('wrote', target, len(all_lines), 'lines')
print('backup', backup)
