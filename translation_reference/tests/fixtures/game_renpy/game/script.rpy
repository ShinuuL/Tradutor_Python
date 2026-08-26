# -*- coding: utf-8 -*-
# Fixture: script Ren'Py de teste para o adapter.
# Contem dialogue, menu, strings em variaveis e translate blocks.

label start:
    "Bom dia, mundo!"
    "Esta e uma string em portugues."
    scene bg house
    "Outro dialogue com acentos: saudacao."
    $ greet = "Ola, viajante!"
    jump chapter1

label chapter1:
    "Capitulo um: o comeco."
    menu:
        "Opcao um":
            "Voce escolheu a primeira opcao."
            jump chapter2
        "Opcao dois":
            "Voce escolheu a segunda opcao."
            jump chapter2
        "Sair":
            return

label chapter2:
    "Capitulo dois: a aventura continua."
    "Texto com placeholders: {player_name} ganhou {gold} moedas."
    $ name = "Personagem Teste"
    "Frase final do teste."

translate portuguese start:
    old "Bom dia, mundo!"
    new "Good morning, world!"
    old "Esta e uma string em portugues."
    new "This is a string in Portuguese."
