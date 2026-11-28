# -*- coding: utf-8 -*-
"""
VIGIA DE FORA DO NOTEBOOK (resto do item 34 da auditoria de 14/11; ele: "Faça", 18/11/2026).

Este arquivo NAO roda no notebook: o programa o copia para o repositorio da pagina do celular
(.github/vigia_notebook.py) e o GitHub o roda sozinho, de segunda a sexta as 13h17 e as 18h17 de Maceio (as duas
desde 19/11/2026; antes so as 18h), mesmo com o notebook
desligado. Ele olha a hora do ultimo envio do notebook ao GitHub (a pagina do celular, ou o "sinal de vida" que o
notebook manda pelo menos a cada 3 horas quando esta ligado) e, se num dia util o notebook nao deu sinal desde as 7h,
a rodada FALHA: o GitHub manda o e-mail de falha para a conta dona do repositorio. Se as chaves VIGIA_EMAIL_* forem
cadastradas no repositorio, manda tambem um e-mail proprio, em palavras simples.

So biblioteca padrao do Python (roda na maquina do GitHub, sem instalar nada).
"""
import datetime
import os
import subprocess
import sys

FUSO = datetime.timezone(datetime.timedelta(hours=-3))      # Maceio; o Brasil nao tem horario de verao desde 2019
HORA_INICIO = 7                                             # o dia do notebook comeca as 7h (tarefa do celular)
DIAS = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')
ARQ_DIAS = os.path.join('.github', 'dias-sem-aviso.txt')     # dias de semana sem expediente (gerado pelo programa)
ASSUNTO = 'Painel do escritório: o notebook não deu sinal num dia útil'
ASSUNTO_TESTE = 'TESTE do vigia do painel do escritório'


def quando(dt):
    d = dt.astimezone(FUSO)
    return '%s %s às %s' % (DIAS[d.weekday()], d.strftime('%d/%m'), d.strftime('%Hh%M'))


def avaliar(ultimo, agora, dias_sem_aviso=()):
    """(ok, texto). ultimo e agora com fuso. Num dia util, falha se o ultimo sinal e de antes das 7h desse dia.

    Conserto de 19/11/2026 (ele: "Faça"): o GitHub atrasa as rodadas agendadas (a das 18h de 18/11 saiu as 23h06).
    Rodada que cai antes das 7h foi marcada para a tarde ANTERIOR e atrasou: confere o dia anterior, em vez de
    desistir ("ainda nao sao 7h"), para o dia nao sumir sem conferencia."""
    ag = agora.astimezone(FUSO)
    if ag.hour < HORA_INICIO:
        dia, qual = ag.date() - datetime.timedelta(days=1), 'ontem'
        atraso = ' Esta conferência estava marcada para a tarde de ontem e o GitHub só a rodou %s.' % quando(ag)
    else:
        dia, qual, atraso = ag.date(), 'hoje', ''
    rotulo = '%s %s' % (DIAS[dia.weekday()], dia.strftime('%d/%m'))
    if dia.weekday() >= 5:
        return True, '%s (%s) é fim de semana: sem conferência.' % (qual.capitalize(), rotulo)
    if dia.isoformat() in dias_sem_aviso:
        return True, '%s (%s) não tem expediente: sem conferência.' % (qual.capitalize(), rotulo)
    inicio = datetime.datetime(dia.year, dia.month, dia.day, HORA_INICIO, tzinfo=FUSO)
    if ultimo is not None and ultimo.astimezone(FUSO) >= inicio:
        return True, 'O notebook deu sinal %s: o último foi %s.%s' % (qual, quando(ultimo), atraso)
    if ultimo is None:
        antes = 'não foi possível ler o último sinal'
    else:
        horas = int((ag - ultimo.astimezone(FUSO)).total_seconds() // 3600)
        antes = 'o último foi %s (há %d horas)' % (quando(ultimo), horas)
    return False, ('O notebook do escritório não deu sinal %s (%s), dia útil, desde as 7h: %s. Enquanto ele estiver '
                   'desligado, suspenso ou sem internet, o painel não lê as publicações, não faz a cópia de segurança e '
                   'não manda o resumo das 7h. Ligue o notebook na tomada e confira o quadro "Saúde do sistema".%s'
                   % (qual, rotulo, antes, atraso))


def ler_ultimo_sinal():
    """Hora do ultimo envio do notebook = hora da versao publicada (o notebook publica sempre uma versao so)."""
    r = subprocess.run(['git', 'log', '-1', '--format=%ct'], capture_output=True, text=True)
    try:
        return datetime.datetime.fromtimestamp(int(r.stdout.strip()), FUSO)
    except ValueError:
        return None


def ler_dias():
    try:
        with open(ARQ_DIAS, encoding='utf-8') as f:
            return {x.strip() for x in f if x.strip() and not x.startswith('#')}
    except OSError:
        return set()


def enviar_email(texto, env, smtp=None, assunto=ASSUNTO):
    """E-mail proprio do vigia, so se as tres chaves estiverem cadastradas no repositorio. Devolve True se mandou."""
    de, senha, para = env.get('VIGIA_EMAIL_DE'), env.get('VIGIA_EMAIL_SENHA'), env.get('VIGIA_EMAIL_PARA')
    if not (de and senha and para):
        return False
    from email.message import EmailMessage
    import smtplib
    m = EmailMessage()
    m['Subject'], m['From'], m['To'] = assunto, de, para
    m.set_content(texto + '\n\nAviso automático do vigia do painel (GitHub), que roda fora do notebook.')
    conexao = smtp or smtplib.SMTP_SSL
    with conexao('smtp.gmail.com', 465) as s:
        s.login(de, ''.join(senha.split()))
        s.send_message(m)
    return True


def main(ultimo=None, agora=None, env=None, dias=None, smtp=None):
    env = os.environ if env is None else env
    ultimo = ler_ultimo_sinal() if ultimo is None else ultimo
    agora = datetime.datetime.now(FUSO) if agora is None else agora
    ok, texto = avaliar(ultimo, agora, ler_dias() if dias is None else dias)
    evento = env.get('GITHUB_EVENT_NAME', '')
    if evento == 'workflow_dispatch' and env.get('VIGIA_TESTE') == 'true':
        # rodada a mao com "teste" marcado (19/11/2026): prova que o e-mail proprio chega, sem esperar o notebook sumir
        try:
            mandou = enviar_email('TESTE: o vigia do notebook consegue mandar e-mail para esta caixa. Quando o '
                                  'notebook ficar sem dar sinal num dia útil, o aviso chega assim.\n\nSituação agora: '
                                  + texto, env, smtp, ASSUNTO_TESTE)
            print('E-mail de teste enviado.' if mandou else 'Sem as três chaves VIGIA_EMAIL_*: e-mail de teste NÃO enviado.')
        except Exception as e:      # noqa: BLE001
            mandou = False
            print('O e-mail de teste falhou: %s' % e)
        return 0 if mandou else 1
    if evento == 'push':        # cada envio do notebook roda o vigia so para mostrar que ele esta vivo; nunca falha
        ok, texto = True, 'Envio do notebook recebido (%s). Vigia ativo.' % quando(agora)
    print(texto)
    resumo = env.get('GITHUB_STEP_SUMMARY')
    if resumo:
        with open(resumo, 'a', encoding='utf-8') as f:
            f.write(('### ' + ('Tudo certo' if ok else 'ATENÇÃO') + '\n\n' + texto + '\n'))
    if ok:
        return 0
    print('::error title=Notebook sem sinal::' + texto)
    try:
        if enviar_email(texto, env, smtp):
            print('E-mail do vigia enviado.')
    except Exception as e:      # noqa: BLE001 - o e-mail proprio e extra; a falha da rodada ja avisa pelo GitHub
        print('O e-mail do vigia falhou: %s' % e)
    return 1


if __name__ == '__main__':
    sys.exit(main())
