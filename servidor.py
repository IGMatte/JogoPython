from time import time, sleep
from threading import Thread
from random import randint
from collections import namedtuple
import socket
import pickle
import winsound

#Define uma classe/tuple para uso com posições e coordenadas
Eixos = namedtuple('Eixos', 'x y')
#Tamanho da arena em X ,Y
# + 50 pixels em Y para display da pontuação
TAM_TELA = Eixos(x = 1024, y = 768)
#Tamanho da sprite usada EM X, Y
SPRITE = Eixos(x = 50, y = 110)
#Ticks por segundo
TPS = 20

#Posições iniciais, definida uma por jogador, lados opostos da arena
class Jogador(Thread):
    """
    Classe base de jogadores, herda e vira uma Thread
    rodando o loop infinito no método run.
    O construtor recebe como parametros:
    game, a sessão GameLogic que o jogador esta atribuido.
    conexao, o socket aberto com o fundo.
    numero, o numero do jogador, definido pela ordem de conexão.
    posicao, a posição inicial deste na arena.
    """
    def __init__(self, game, conexao, numero, posicao):
        Thread.__init__(self)
        self.game = game
        self.conexao = conexao
        self.numero = numero
        self.posicao = posicao
        self.prox_posicao = posicao
        self.direcao = 'direita'
        self.acertos = 0
        self.atingido = False
        self.soqueando = False
        self.animacao = False
        self.pronto = False
        print(f"Jogador {self.numero} Conectado!")


    def prox_movimento(self, direcao):
        """
        Troca a direção atual do personagem e o movimento do proximo tick.
        """
        if direcao == 'cima':
            self.prox_posicao = Eixos(x = self.posicao.x, y = self.posicao.y - 5)
        elif direcao == 'baixo':
            self.prox_posicao = Eixos(x = self.posicao.x, y = self.posicao.y + 5)
        elif direcao == 'esquerda':
            self.prox_posicao = Eixos(x = self.posicao.x - 5, y = self.posicao.y)
            self.direcao = direcao
        elif direcao == 'direita':
            self.prox_posicao = Eixos(x = self.posicao.x + 5, y = self.posicao.y)
            self.direcao = direcao


    def run(self):
        """
        Loop da Thread, preparando o jogo, recebe e processa
        os comandos enviados.
        """
        while True:
            dados = self.conexao.recv(2048)
            comando, arg = pickle.loads(dados)
            if comando == 'Iniciar':
                resposta = ('Preparar', self.numero)
                self.conexao.send(pickle.dumps(resposta))
                self.pronto = True
            elif comando == 'Mover':
                self.prox_movimento(arg)
            elif comando == 'Soquear':
                self.soqueando = True

class GameLogic(Thread):
    """
    Classe base para logica de uma partida, inicia uma Thread
    rodando o loop contido em run.
    Argumentos: tamanho da arena em (x,y)
    ticks por segundo desejados.
    """
    def __init__(self, t_arena, tps):
        Thread.__init__(self)
        self.t_arena = t_arena
        self.tps = tps
        self.jogadores = []

    def run(self):
        """
        Realiza o movimento de todos os jogadores se não houver colisão,
        Determina se algum jogador acertou um soco no tick atual,
        Atualiza o numero de acertos e envia os dados atualizados
        à todos os jogadores da sessão.
        Aguarda o tempo necessário para o tick ter ocorrido em 1/TPS.
        """
        while True:
            prox_tick = time() + (1/TPS)
            for jogador in self.jogadores:
                self.mover_jogador(jogador)
            for jogador in self.jogadores:
                if jogador.soqueando:
                    self.soqueando(jogador)
                    jogador.animacao = True
                else:
                    jogador.animacao = False
            for jogador in self.jogadores:
                if jogador.atingido:
                    jogador.acertos += 1
                    jogador.atingido = False
            self.atualizar_jogadores()
            sleep(prox_tick - time())


    def novo_jogador(self, conexao):
        """
        Instancia e adiciona à sessão um novo jogador,
        definindo numero, posição e iniciando uma nova thread para este.
        retorna a thread jogador para o loop principal.
        Argumentos: o socket criado ao aceitar à conexão.
        """
        numero_jogador = len(self.jogadores) + 1
        posicao_inicial = Eixos(x=abs(randint(0, TAM_TELA.x) - SPRITE.x),
                         y=abs(randint(0, TAM_TELA.y) - SPRITE.y))
        jogador = Jogador(self, conexao, numero_jogador, posicao_inicial)
        self.jogadores.append(jogador)
        jogador.start()


    def atualizar_jogadores(self):
        """
        Monta uma lista de dicionários com as informações de cada jogador,
        serializa toda a mensagem e envia à cada jogador pelo seu socket.
        """
        pacote = []
        for jogador in self.jogadores:
            if jogador.pronto:
                dados = {'numero': jogador.numero,
                        'posicao': jogador.posicao,
                        'direcao': jogador.direcao,
                        'acertos': jogador.acertos,
                        'soqueando': jogador.soqueando,
                        'animacao': jogador.animacao}
                pacote.append(dados)
        if pacote:
            pacote.insert(0, 'Atualizar')
            for jogador in self.jogadores:
                jogador.conexao.send(pickle.dumps(pacote))


    def soqueando(self, jogador):
        """
        Testa se jogador acertou um soco nos outros jogador participantes da sessão,
        um soco é definido como posição + tamanho da sprite + tamanho do soco,
        tamanho do soco é passado no offset de testar_colisao_jogador.
        Argumentos: o jogador que iniciou o soco.
        """
        if jogador.direcao == 'direita':
            for jogador2 in self.jogadores:
                if jogador != jogador2:
                    if testar_colisao_jogador(jogador.posicao, jogador2.posicao, Eixos(x = 5, y = 0)):
                        jogador2.atingido = True
        elif jogador.direcao == 'esquerda':
            for jogador2 in self.jogadores:
                if jogador != jogador2:
                    if testar_colisao_jogador(jogador.posicao, jogador2.posicao, Eixos(x = -5, y = 0)):
                        jogador2.atingido = True
        jogador.soqueando = False


    def mover_jogador(self, jogador):
        """
        Realiza os testes de colisão,
        caso não haja outro jogador ou não haja colisão,
        atualiza a posição do jogador.
        Argumentos: o jogador à ser movimentado.
        """
        if jogador.posicao != jogador.prox_posicao:
            if not self.testar_colisao_borda(jogador.prox_posicao):
                for jogador2 in self.jogadores:
                    if jogador != jogador2:
                        if testar_colisao_jogador(jogador.prox_posicao, jogador2.posicao):
                            return
                jogador.posicao = jogador.prox_posicao
                return


    def testar_colisao_borda(self, jogador):
        """
        Testa se a sprite do jogador não esta invandindo à borda da arena.
        Argumentos: o jogador à ser testado.
        """
        if (jogador.x + SPRITE.x) < self.t_arena.x and \
        (jogador.y + SPRITE.y) < self.t_arena.y and \
        jogador.x > 0 and jogador.y > 0:
            return False
        return True

            
def testar_colisao_jogador(jogador, jogador2, offset = Eixos(x = 0, y = 0)):
    """
    Testa pela colisão simples entre entre dois jogadores,
    assume-se que o jogador é um retangulo com angulos iguais e paralelos à borda.
    """
    if (jogador.x + offset.x) < (jogador2.x + SPRITE.x) and \
    (jogador.x + SPRITE.x + offset.x) > jogador2.x and \
    (jogador.y + offset.y) < (jogador2.y + SPRITE.y) and \
    (jogador.y + SPRITE.y + offset.y) > jogador2.y:
        return True
    return False
    
            
def main():
    """
    Instancia uma sessão de GameLogic, iniciando sua thread.
    Configura um socket em modo servidor,
    entra em um loop infinito, aguardando conexão dos jogadores
     até o limite estabelecido, processa a nova conexão,
    a game_thread instancia um novo jogador à sessão.
    """
    game_thread = GameLogic(TAM_TELA, TPS)
    game_thread.start()

    game_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    game_server.bind(('127.0.0.1', 8000))
    while True:
        game_server.listen(2)
        print("Aguardando Jogadores...")
        (nova_conexao, endereco) = game_server.accept()
        print(f"Novo Jogar em {endereco}")
        game_thread.novo_jogador(nova_conexao)

if __name__ == '__main__':
    main()
