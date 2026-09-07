# Segurança e tratamento de dados

## Contexto atual

- Utilizadores: **apenas equipa interna** de auditoria.
- Dados: tipicamente **informação corporativa** (nome, email, sistema, perfil). Sem
  dados especiais RGPD esperados.
- Envio a terceiros: **não é uma preocupação para já** — os dados dos tickets podem ser
  enviados à API da Anthropic para extração.

Este documento regista, ainda assim, as costuras deixadas prontas para o dia em que um
cliente imponha restrições — porque é barato desenhá-las agora e caro reescrever depois.

## Costura de pseudonimização (desligada por omissão)

Existe um **ponto único** no fluxo, imediatamente antes da chamada à API, onde os dados
podem ser redigidos/pseudonimizados:

- Substituição de nomes/emails por tokens reversíveis (`PESSOA_01`, `EMAIL_01`) antes do
  envio; re-substituição no retorno.
- Ativável por flag de config (`privacy.pseudonymize: true`), por cliente.
- Quando ativa, o LLM nunca vê identidades reais; a comparação de SoD continua a
  funcionar porque opera sobre os tokens (a mesma pessoa → o mesmo token).

Enquanto desligada, não há impacto no fluxo normal.

## Modo sem chamadas externas (futuro)

A arquitetura permite substituir a camada de extração por um extrator local (regex/
heurísticas por profile, ou um modelo local) para clientes que proíbam qualquer envio
externo. As camadas de modelo canónico e de avaliação não mudam.

## Trilho de auditoria (defensabilidade da ferramenta)

Como o output pode vir a alimentar papéis de trabalho, cada extração regista:

- versão do **modelo** usado;
- versão/hash do **prompt**;
- **resposta bruta** do modelo;
- profile e sua versão;
- data/hora e utilizador.

Isto vai para a aba `Rastreio` do workpaper e permite reproduzir e defender qualquer
resultado. Combinado com o motor de regras determinístico e os seus testes `pytest`, a
ferramenta é auditável de ponta a ponta.

## Gestão da chave de API

- A chave da API Anthropic **nunca** fica em código nem em ficheiros versionados.
- Lê-se de variável de ambiente / gestor de segredos (`.env` fora do git, ou o gestor de
  segredos da cloud quando migrar).
- Documentar o procedimento de rotação no runbook de operação.

## Retenção

Na v1 os dados vivem **só em sessão** — fechar a app não guarda nada. A única persistência
é a que o auditor escolhe ao **exportar** o workpaper, que passa a ser gerido como
qualquer papel de trabalho (nos repositórios de auditoria, com as suas próprias regras de
retenção).
