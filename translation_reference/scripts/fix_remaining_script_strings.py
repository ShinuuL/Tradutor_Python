from pathlib import Path
p=Path(r'D:\Segredo\sukidara\extracted\script.rpy')
txt=p.read_text(encoding='utf-8-sig')
repl={
    'default mc_name = "僕"': 'default mc_name = "Me"',
    'SetScreenVariable("feedback_msg", "ビクッ！？（マズい！）")': 'SetScreenVariable("feedback_msg", "Flinch!? (Bad!)")',
    'textbutton "▶ 抜く":': 'textbutton "▶ Pull out":',
    'mc_name "「おばさん、出るっ……！」"': 'mc_name "\"Auntie, I\'m cumming...!\""',
    '"（僕は慌てて有希の口を強く塞いだ）"': '"(I hurriedly covered Yuki\'s mouth tightly.)"',
    '"ドアが開いて、おばさんが入ってきた。"': '"The door opened, and Auntie came in."',
    '"おばさんに見られてしまった。冷たい軽蔑の目が突き刺さる。"': '"Auntie saw us. Her cold, contemptuous eyes pierced me."',
    'mc_name "「有希、出るっ……！」"': 'mc_name "\"Yuki, I\'m cumming...!\""',
}
for a,b in repl.items():
    if a not in txt:
        print('MISSING', a)
    txt=txt.replace(a,b,1)
p.write_text(txt, encoding='utf-8', newline='')
print('done')
