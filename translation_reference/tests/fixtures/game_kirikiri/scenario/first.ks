; Kirikiri script fixture para testes
*start
[jump storage="chapter1.ks" target="*begin"]

*chapter1
Dialogo simples entre comandos.
Essa e a segunda linha de dialogo.

[eval exp="text = 'Ola, mundo!'"]
[dialog text="Texto via dialog tag"]

[if exp="f.flag == 1"]
[eval exp="f.flag = 0"]
[endif]

[playbgm storage="bgm01.ogg"]
[wait time=1000]
[stop]

[macro name="testmacro"]
Texto dentro do macro.
Segunda linha do macro.
[endmacro]

Macro apos endmacro nao e mais macro.
[return]
