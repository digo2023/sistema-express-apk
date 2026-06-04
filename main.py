# -*- coding: utf-8 -*-
"""GESTÃO DE ESTOQUE EXPRESS COLORADO — Botões Reais Funcionais.

Correção definitiva para tela estática:
- Usa apenas Button padrão do Kivy para cards e ações.
- Não usa ButtonBehavior em layouts dentro do ScrollView.
- Área de rolagem fica livre e funcional.
- Cada card chama o núcleo operacional ao tocar.
"""
import os
import re
import sys
import queue
import threading
import traceback
from pathlib import Path

os.environ.setdefault("SISTEMA_EXPRESS_APK", "1")
os.environ.setdefault("SISTEMA_EXPRESS_UI_PREMIUM", "1")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle, Rectangle, Ellipse
from kivy.metrics import dp
from kivy.resources import resource_find
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ROOT_DIR = Path(__file__).resolve().parent

NAVY = (0.004, 0.010, 0.026, 1)
CARD = (0.011, 0.031, 0.067, 0.98)
CARD_2 = (0.016, 0.044, 0.092, 0.98)
BLUE = (0.000, 0.565, 1.000, 1)
GOLD = (1.000, 0.590, 0.020, 1)
GREEN = (0.040, 0.820, 0.410, 1)
WHITE = (0.940, 0.960, 0.985, 1)
MUTED = (0.655, 0.708, 0.790, 1)
BORDER_BLUE = (0.000, 0.480, 1.000, 0.70)
BORDER_GOLD = (1.000, 0.545, 0.000, 0.70)
BORDER_DIM = (0.100, 0.285, 0.570, 0.40)


def preparar_imports_sistema():
    import importlib

    candidatos = [ROOT_DIR, Path.cwd()]
    for env_name in ("ANDROID_PRIVATE", "ANDROID_APP_PATH", "PYTHONHOME"):
        valor = os.environ.get(env_name)
        if valor:
            candidatos.append(Path(valor))
            candidatos.append(Path(valor) / "app")

    for item in candidatos:
        try:
            texto = str(item)
            if texto and texto not in sys.path:
                sys.path.insert(0, texto)
        except Exception:
            pass

    pacote = importlib.import_module("sistema_express")
    pacote_paths = list(getattr(pacote, "__path__", []))
    for caminho in pacote_paths:
        if caminho and caminho not in sys.path:
            sys.path.insert(0, caminho)

    cfg = importlib.import_module("sistema_express.configuracao")
    mods = importlib.import_module("sistema_express.modulos")
    sys.modules["configuracao"] = cfg
    sys.modules["modulos"] = mods
    return pacote_paths[0] if pacote_paths else str(ROOT_DIR / "sistema_express")


class Fundo(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*NAVY)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(0.0, 0.25, 0.60, 0.18)
            self._halo_azul = Ellipse()
            Color(1.0, 0.50, 0.0, 0.12)
            self._halo_ouro = Ellipse()
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._halo_azul.pos = (self.width - dp(230), self.height - dp(195))
        self._halo_azul.size = (dp(285), dp(285))
        self._halo_ouro.pos = (-dp(120), -dp(90))
        self._halo_ouro.size = (dp(245), dp(245))


class Painel(BoxLayout):
    def __init__(self, cor=CARD, borda=BORDER_BLUE, raio=18, **kwargs):
        super().__init__(**kwargs)
        self.cor = cor
        self.borda = borda
        self.raio = raio
        with self.canvas.before:
            Color(*self.cor)
            self._bg = RoundedRectangle(radius=[dp(self.raio)])
            Color(*self.borda)
            self._line = Line(width=dp(1.15), rounded_rectangle=(0, 0, 1, 1, dp(self.raio)))
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(self.raio))


class PremiumButton(Button):
    def __init__(self, cor=CARD_2, borda=BORDER_BLUE, raio=18, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = WHITE
        self.markup = True
        self.bold = True
        self.halign = "center"
        self.valign = "middle"
        self.font_size = kwargs.get("font_size", "13sp")
        self.cor = cor
        self.borda = borda
        self.raio = raio
        with self.canvas.before:
            Color(*self.cor)
            self._bg = RoundedRectangle(radius=[dp(self.raio)])
            Color(*self.borda)
            self._line = Line(width=dp(1.15), rounded_rectangle=(0, 0, 1, 1, dp(self.raio)))
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0] - dp(10), val[1])))

    def _update_canvas(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(self.raio))


class EntradaTerminal:
    def __init__(self):
        self._fila = queue.Queue()

    def enviar(self, texto: str):
        self._fila.put(str(texto or "") + "\n")

    def readline(self):
        return self._fila.get()

    def readable(self):
        return True


class SaidaTerminal:
    encoding = "utf-8"

    def __init__(self, callback):
        self.callback = callback
        self._buffer = ""

    def write(self, texto):
        if not texto:
            return 0
        texto = ANSI_RE.sub("", str(texto))
        self._buffer += texto
        if "\n" in self._buffer or len(self._buffer) > 240:
            parte = self._buffer
            self._buffer = ""
            self.callback(parte)
        return len(texto)

    def flush(self):
        if self._buffer:
            parte = self._buffer
            self._buffer = ""
            self.callback(parte)

    def isatty(self):
        return False


class TelaPrincipal(Fundo):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = NAVY
        self.entrada_terminal = EntradaTerminal()
        self.executando = False
        self.thread_sistema = None
        self.linhas = []
        self.max_linhas_interface = 5000

        self._montar_header()
        self._montar_scroll()
        self._montar_nav()
        self._montar_console_overlay()
        self._pedir_permissoes_android()

    def _asset(self, nome):
        return resource_find(f"sistema_express/recursos/{nome}") or resource_find(nome) or ""

    def _label(self, text, fs="13sp", color=WHITE, bold=False, halign="left"):
        lb = Label(text=text, font_size=fs, color=color, bold=bold, markup=True, halign=halign, valign="middle")
        lb.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        return lb

    def _montar_header(self):
        header = BoxLayout(
            orientation="horizontal", spacing=dp(9), padding=(dp(10), dp(8), dp(10), 0),
            size_hint=(1, None), height=dp(104), pos_hint={"top": 1}
        )
        logo_card = Painel(cor=(0.006, 0.022, 0.050, 0.95), borda=BORDER_BLUE, raio=22,
                           size_hint=(None, 1), width=dp(92), padding=dp(5))
        logo_card.add_widget(Image(source=self._asset("app_icon.png"), allow_stretch=True, keep_ratio=True))
        header.add_widget(logo_card)

        textos = BoxLayout(orientation="vertical")
        textos.add_widget(self._label("[color=1AA9FF][b]GESTÃO DE ESTOQUE[/b][/color]", "13sp", BLUE, True))
        textos.add_widget(self._label("[b]EXPRESS COLORADO[/b]", "20sp", WHITE, True))
        textos.add_widget(self._label("[color=FF9A12][b]Operação, compras e conferência[/b][/color]", "12sp", GOLD, True))
        header.add_widget(textos)

        alertas = PremiumButton(text="[b]ALERTAS[/b]", font_size="10sp", size_hint=(None, None), size=(dp(74), dp(54)),
                                cor=(0.006, 0.022, 0.050, 0.95), borda=BORDER_DIM, raio=16)
        alertas.bind(on_release=lambda *_: self.executar_acao("8", "Alertas"))
        header.add_widget(alertas)
        self.add_widget(header)

    def _montar_scroll(self):
        scroll = ScrollView(
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(6),
            scroll_type=["content", "bars"],
            effect_cls="ScrollEffect",
        )
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=(dp(10), dp(108), dp(10), dp(84)), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        self.add_widget(scroll)

        title = Painel(orientation="horizontal", size_hint_y=None, height=dp(96), padding=dp(11), spacing=dp(8),
                       cor=(0.008, 0.024, 0.052, 0.86), borda=BORDER_DIM, raio=22)
        left = BoxLayout(orientation="vertical")
        left.add_widget(self._label("[b]Painel Operacional[/b]", "24sp", WHITE, True))
        left.add_widget(self._label("Sistema premium de controle diário da unidade.", "12sp", MUTED))
        title.add_widget(left)
        status = Painel(cor=(0.010, 0.055, 0.060, 0.72), borda=(0.04, 0.82, 0.41, 0.50),
                        size_hint=(None, None), size=(dp(132), dp(42)), padding=dp(6), raio=14)
        status.add_widget(self._label("[color=0AE066][b]ONLINE[/b][/color]", "12sp", GREEN, True, "center"))
        title.add_widget(status)
        content.add_widget(title)

        kpis = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(186))
        for titulo, valor, rodape, simbolo, cor, borda, cmd in [
            ("Itens cadastrados", "1.248", "produtos ativos", "EST", BLUE, BORDER_BLUE, "4"),
            ("Estoque baixo", "23", "reposição necessária", "ALT", GOLD, BORDER_GOLD, "8"),
            ("OC pendentes", "12", "compras abertas", "OC", BLUE, BORDER_BLUE, "10"),
            ("Consumo do dia", "R$ 18.542", "atualizado 10:45", "R$", GOLD, BORDER_GOLD, "12"),
        ]:
            kpis.add_widget(self._botao_kpi(titulo, valor, rodape, simbolo, cor, borda, cmd))
        content.add_widget(kpis)

        quick = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(116))
        quick.add_widget(self._botao_grande("Nova entrada", "Registrar entrada de produto", "ENT", "2", BLUE, BORDER_BLUE))
        quick.add_widget(self._botao_grande("Nova saída", "Baixar consumo por turno", "SAI", "3", GOLD, BORDER_GOLD))
        content.add_widget(quick)

        sec = self._label("[b]Funções principais[/b]", "17sp", WHITE, True)
        sec.size_hint_y = None
        sec.height = dp(30)
        content.add_widget(sec)

        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(585))
        acoes = [
            ("Estoque", "Produtos, saldos e localização", "EST", "4", BLUE, BORDER_BLUE),
            ("Conferência", "Ajuste seguro de estoque", "CONF", "6", BLUE, BORDER_BLUE),
            ("Planejamento", "Analítico e consumo", "PLAN", "9", GOLD, BORDER_GOLD),
            ("Relatórios", "PDF, Excel e consultas", "REL", "7", BLUE, BORDER_BLUE),
            ("Compras / OC", "Necessário x ordem", "OC", "10", GOLD, BORDER_GOLD),
            ("Faltantes", "Riscos e divergências", "FAL", "7", GOLD, BORDER_GOLD),
            ("Backup", "Proteger dados", "BKP", "11", BLUE, BORDER_BLUE),
            ("Funções", "Manual do sistema", "AJD", "14", GOLD, BORDER_GOLD),
            ("Código de barras", "Leitura e busca", "COD", "15", BLUE, BORDER_BLUE),
            ("Resumo", "Painel técnico", "RES", "12", BLUE, BORDER_BLUE),
        ]
        for nome, subtitulo, simb, cmd, cor, borda in acoes:
            grid.add_widget(self._botao_grande(nome, subtitulo, simb, cmd, cor, borda))
        content.add_widget(grid)

    def _botao_kpi(self, titulo, valor, rodape, simbolo, cor, borda, cmd):
        cor_hex = "1AA9FF" if cor == BLUE else "FF9A12"
        texto = (
            f"[color={cor_hex}][size=16sp][b]{simbolo}[/b][/size][/color]\n"
            f"[size=11sp]{titulo}[/size]\n"
            f"[size=21sp][b]{valor}[/b][/size]\n"
            f"[color={cor_hex}][size=10sp]{rodape}[/size][/color]"
        )
        b = PremiumButton(text=texto, font_size="12sp", cor=CARD_2, borda=borda, raio=20)
        b.bind(on_release=lambda *_: self.executar_acao(cmd, titulo))
        return b

    def _botao_grande(self, titulo, subtitulo, simbolo, cmd, cor, borda):
        cor_hex = "1AA9FF" if cor == BLUE else "FF9A12"
        texto = (
            f"[color={cor_hex}][size=16sp][b]{simbolo}[/b][/size][/color]\n"
            f"[size=15sp][b]{titulo}[/b][/size]\n"
            f"[size=10sp]{subtitulo}[/size]\n"
            f"[color={cor_hex}][size=18sp][b]>[/b][/size][/color]"
        )
        b = PremiumButton(text=texto, font_size="12sp", cor=CARD_2, borda=borda, raio=20)
        b.bind(on_release=lambda *_: self.executar_acao(cmd, titulo))
        return b

    def _montar_nav(self):
        nav = Painel(orientation="horizontal", size_hint=(1, None), height=dp(66), padding=dp(4), spacing=dp(4),
                     cor=(0.006, 0.020, 0.044, 0.98), borda=BORDER_BLUE, raio=20, pos_hint={"x": 0, "y": 0})
        for texto, cmd in [
            ("Início", None),
            ("Painel", "12"),
            ("Ações", None),
            ("Relatórios", "7"),
            ("Mais", "14"),
        ]:
            b = PremiumButton(text=f"[b]{texto}[/b]", font_size="12sp",
                              cor=(0.014, 0.038, 0.078, 0.96),
                              borda=BORDER_GOLD if texto == "Ações" else (0, 0, 0, 0), raio=16)
            if cmd:
                b.bind(on_release=lambda _inst, c=cmd, t=texto: self.executar_acao(c, t))
            nav.add_widget(b)
        self.add_widget(nav)

    def _montar_console_overlay(self):
        self.overlay = FloatLayout(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.overlay.opacity = 0
        self.overlay.disabled = True
        with self.overlay.canvas.before:
            Color(0, 0, 0, 0.58)
            self._shade = Rectangle(pos=self.overlay.pos, size=self.overlay.size)
        self.overlay.bind(pos=lambda *_: setattr(self._shade, "pos", self.overlay.pos),
                          size=lambda *_: setattr(self._shade, "size", self.overlay.size))

        card = Painel(orientation="vertical", cor=(0.006, 0.014, 0.030, 0.985), borda=BORDER_BLUE, raio=22,
                      size_hint=(0.94, 0.67), pos_hint={"x": 0.03, "y": 0.16}, padding=dp(8), spacing=dp(6))
        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(42))
        top.add_widget(self._label("[b]Execução segura[/b]", "15sp", GOLD, True))
        limpar = PremiumButton(text="LIMPAR", font_size="11sp", size_hint=(None, 1), width=dp(84),
                               cor=(0.010, 0.025, 0.050, 0.96), borda=BORDER_DIM, raio=12)
        limpar.bind(on_release=lambda *_: self.limpar_console())
        top.add_widget(limpar)
        card.add_widget(top)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=dp(4))
        self.saida = Label(text="", color=WHITE, font_name="RobotoMono-Regular", font_size="11sp",
                           markup=False, size_hint_y=None, halign="left", valign="top")
        self.saida.bind(texture_size=self._ajustar_altura)
        self.scroll.add_widget(self.saida)
        card.add_widget(self.scroll)

        bottom = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(54), spacing=dp(7))
        voltar = PremiumButton(text="< VOLTAR", font_size="12sp", size_hint_x=None, width=dp(96),
                               cor=(0.010, 0.044, 0.088, 0.96), borda=BORDER_BLUE, raio=14)
        voltar.bind(on_release=lambda *_: self.enviar_voltar())
        bottom.add_widget(voltar)
        self.campo = TextInput(hint_text="Digite a informação solicitada...", multiline=False,
                               font_size="15sp", foreground_color=WHITE, hint_text_color=(0.62, 0.66, 0.72, 1),
                               background_normal="", background_active="", background_color=(0.010, 0.025, 0.050, 0.96),
                               cursor_color=GOLD, padding=(dp(12), dp(14), dp(12), dp(12)))
        self.campo.bind(on_text_validate=lambda *_: self.enviar_linha())
        bottom.add_widget(self.campo)
        enviar = PremiumButton(text="ENVIAR", font_size="12sp", size_hint_x=None, width=dp(90),
                               cor=(0.140, 0.078, 0.015, 0.96), borda=BORDER_GOLD, raio=14)
        enviar.bind(on_release=lambda *_: self.enviar_linha())
        bottom.add_widget(enviar)
        card.add_widget(bottom)

        self.overlay.add_widget(card)
        self.add_widget(self.overlay)

    def _pedir_permissoes_android(self):
        try:
            from android.permissions import request_permissions, Permission
            perms = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            for nome in ("READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO", "MANAGE_EXTERNAL_STORAGE"):
                valor = getattr(Permission, nome, None)
                if valor:
                    perms.append(valor)
            request_permissions(perms)
        except Exception:
            pass

    def abrir_console(self):
        self.overlay.disabled = False
        self.overlay.opacity = 1

    def _ajustar_altura(self, *_):
        self.saida.text_size = (self.scroll.width - dp(12), None)
        self.saida.height = max(self.saida.texture_size[1] + dp(20), self.scroll.height)

    def limpar_console(self):
        self.linhas = []
        self.saida.text = "Console limpo. Escolha uma função ou informe os dados solicitados.\n"

    def _append_ui(self, texto):
        self.linhas.extend(str(texto).splitlines(True))
        if len(self.linhas) > self.max_linhas_interface:
            self.linhas = self.linhas[-self.max_linhas_interface:]
        self.saida.text = "".join(self.linhas)
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 0), 0.05)

    def escrever(self, texto):
        Clock.schedule_once(lambda *_: self._append_ui(texto), 0)

    def iniciar_sistema(self):
        if self.executando:
            return
        self.executando = True
        self.abrir_console()
        self.escrever("\nIniciando Gestão de Estoque Express Colorado...\n")
        self.thread_sistema = threading.Thread(target=self._executar_sistema, daemon=True)
        self.thread_sistema.start()

    def executar_acao(self, comando, titulo=""):
        self.abrir_console()
        self.escrever(f"\n> {titulo}\n")
        if not self.executando:
            self.iniciar_sistema()
            Clock.schedule_once(lambda *_: self._enviar_texto(comando, eco=True), 1.0)
        else:
            self._enviar_texto(comando, eco=True)

    def _executar_sistema(self):
        entrada_original = sys.stdin
        saida_original = sys.stdout
        erro_original = sys.stderr
        cwd_original = os.getcwd()
        saida = SaidaTerminal(self.escrever)
        try:
            import importlib
            sys.stdin = self.entrada_terminal
            sys.stdout = saida
            sys.stderr = saida
            sistema_dir = preparar_imports_sistema()
            try:
                os.chdir(str(sistema_dir))
            except Exception:
                pass
            modulo = importlib.import_module("sistema_express.iniciar")
            principal = getattr(modulo, "principal", None)
            if not callable(principal):
                raise RuntimeError("Função principal() não encontrada em sistema_express.iniciar")
            principal()
        except SystemExit:
            pass
        except BaseException:
            traceback.print_exc()
        finally:
            try:
                saida.flush()
            except Exception:
                pass
            sys.stdin = entrada_original
            sys.stdout = saida_original
            sys.stderr = erro_original
            try:
                os.chdir(cwd_original)
            except Exception:
                pass
            self.executando = False
            self.escrever("\nSistema finalizado com segurança.\n")

    def enviar_linha(self):
        texto = self.campo.text
        self.campo.text = ""
        self._enviar_texto(texto, eco=True)

    def enviar_voltar(self):
        self._enviar_texto("999", eco=False)
        self.escrever("\n< Voltar\n")

    def _enviar_texto(self, texto, eco=False):
        if eco:
            self.escrever(f"{texto}\n")
        self.entrada_terminal.enviar(texto)


class SistemaExpressApp(App):
    title = "Gestão de Estoque Express Colorado"
    icon = "icon.png"

    def build(self):
        return TelaPrincipal()


if __name__ == "__main__":
    SistemaExpressApp().run()
