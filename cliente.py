import socket
from threading import Thread
from collections import namedtuple
import pickle
import pygame
import winsound

#Define uma classe/tuple para uso com posições e coordenadas
Eixos = namedtuple('Eixos', 'x y')
#Tamanho da tela, considerar Tamanho da arena
# + 50 pixels em Y para display da pontuação
TAM_TELA = Eixos(x = 1024, y = 768)
#Define cores usadas
PRETO = (0, 0, 0)
BRANCO = (255, 255, 255)
#Carrega as imagens e sprites usadas
IMAGEM_FUNDO = "fundo.jpg"
JOGADOR_ESQUERDA = "parado_esquerda.png"
JOGADOR_DIREITA = "parado_direita.png"
JOGADOR_SOQUEANDO_ESQUERDA = "soco_esquerda.png"
JOGADOR_SOQUEANDO_DIREITA = "soco_direita.png"
POSICAO_IMAGEM_FUNDO = (0, 0)

class Cliente(Thread):
    """
    Instancia à Thread responsavel pelo networking,
    tambem contem as informações relevantes da partida.
    """
    def __init__(self, ip, porta):
        Thread.__init__(self)
        self.conexao = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conexao.connect((ip, porta))
        self.jogadores = []
        self.prox_movimento = ''
        self.soqueando = False
        self.numero = ''

        comando = ['Iniciar', '']
        self.conexao.send(pickle.dumps(comando))

    def run(self):
        """
        Loop infinito da Thread que recebe e processa
        os updates do servidor.
        """
        while True:
            dados = self.conexao.recv(2048)
            comando, *arg = pickle.loads(dados)
            if comando == 'Atualizar':
                self.jogadores = arg
            elif comando == 'Preparar':
                self.numero = arg


    def mover(self, event):
        """
        Processa o evento de tecla e guarda o ultimo movimento.
        Caso haja soco, este irá sobreescrever movimentos no envio.
        Argumentos: evento de tecla pressionada pygame.
        """
        if not event:
            self.prox_movimento = ''
        elif event.key == pygame.K_LEFT:
            self.prox_movimento = "esquerda"
        elif event.key == pygame.K_RIGHT:
            self.prox_movimento = "direita"
        elif event.key == pygame.K_UP:
            self.prox_movimento = "cima"
        elif event.key == pygame.K_DOWN:
            self.prox_movimento = "baixo"
        elif event.key == pygame.K_SPACE:
            self.soqueando = True

    def atualizar(self):
        """
        Envia ao servidor o ultimo movimento ou estar dando soco.
        """
        dados = []
        if self.soqueando:
            dados.append('Soquear')
            dados.append('')
            self.soqueando = False
        elif self.prox_movimento:
            dados.append('Mover')
            dados.append(self.prox_movimento)
        if dados:
            self.conexao.send(pickle.dumps(dados))

class ScreenHandler():
    """
    Controla os aspectos da Tela do jogo.
    Argumentos: Tamanho da tela(x, y), Titulo da caixa
    """
    def __init__(self, tam_tela, titulo):
        pygame.init()
        pygame.display.set_caption(titulo)

        self.tam_tela = tam_tela
        self.tela = pygame.display.set_mode(self.tam_tela)

        self.font = pygame.font.SysFont('Calibri', 24, True, False)
        self.fundo = pygame.image.load(IMAGEM_FUNDO).convert()
        self.jogador_esquerda = pygame.image.load(JOGADOR_ESQUERDA).convert_alpha()
        self.jogador_direita = pygame.image.load(JOGADOR_DIREITA).convert_alpha()

        self.jogador_soco_esquerda = pygame.image.load(JOGADOR_SOQUEANDO_ESQUERDA).convert_alpha()
        self.jogador_soco_direita = pygame.image.load(JOGADOR_SOQUEANDO_DIREITA).convert_alpha()

    def atualizar(self, cliente):
        """
        Realizada o desenho em tela dos jogadores baseado em suas posições e direções.
        Argumento: Instancia do Cliente com as informações recebidas do servidor.
        """
        self.tela.fill(PRETO)
        self.tela.blit(self.fundo, POSICAO_IMAGEM_FUNDO)
        for jogador in cliente.jogadores:
            numero_jogador = jogador['numero']
            acertos_jogador = jogador['acertos']
            texto_linha1 = self.font.render("Jogador " + str(numero_jogador), True, BRANCO)
            texto_linha2 = self.font.render("Acertos: "+ str(acertos_jogador), True, BRANCO)
            posicao_linha1 = (self.tam_tela.x / 2 * (numero_jogador - 1), self.tam_tela.y - 50)
            posicao_linha2 = (self.tam_tela.x / 2 * (numero_jogador - 1), self.tam_tela.y - 25)
            self.tela.blit(texto_linha1, posicao_linha1)
            self.tela.blit(texto_linha2, posicao_linha2)
            
            #verifica o lado que o jogador está virado e se há a animação de soco
            if (jogador['direcao'] == 'direita' and not jogador['animacao']):
                self.tela.blit(self.jogador_direita, jogador['posicao'])

            if (jogador['direcao'] == 'direita' and jogador['animacao']):
                print("entrei")
                self.tela.blit(self.jogador_soco_direita, jogador['posicao'])

            if (jogador['direcao'] == 'esquerda' and not jogador['animacao']):
                self.tela.blit(self.jogador_esquerda, jogador['posicao'])
                
            if (jogador['direcao'] == 'esquerda' and jogador['animacao']):
                print("entrei2")
                #jogador['posicao'] = Eixos(x = jogador['posicao'].x - 61,y = jogador['posicao'].y)
                self.tela.blit(self.jogador_soco_esquerda, jogador['posicao'])
            
        pygame.display.flip()



def main():
    """
    Rotina principal, instanciam as classes que gerenciam
    a tela, as conexões de rede, entra no loop de eventos
    que controla o jogo, atualiza tela, rede e controla o FPS.
    """
    tela = ScreenHandler(TAM_TELA, "Jogo 1v1 - Sistemas Distribuídos 2018/02")
    cliente = Cliente('127.0.0.1', 8000)
    cliente.start()
    relogio = pygame.time.Clock()
    finalizou = False
    while not finalizou:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                finalizou = True
            elif event.type == pygame.KEYDOWN:
                cliente.mover(event)
            elif event.type == pygame.KEYUP:
                cliente.mover('')
        tela.atualizar(cliente)
        cliente.atualizar()
        relogio.tick(60)
    pygame.quit()

if __name__ == '__main__':
    main()
