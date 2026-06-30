# Estado do Projeto Laura

> Atualizado em: 2026-06-30
> Sessão: Fase 6 — Fiada 6c+ — Gestão completa de entrega (edição, exclusão, foto)

---

## Saúde do Projeto

🟡 Amarelo

- Fundação concluída.
- Ciclo documental completo: orçamento → PFM → A PAGAR → PIX → PAGO → NF-e vinculada.
- PC 2.0 (PDF) implementado mas ainda não validado em produção — DOCX continua funcionando.
- Modo teste operacional e isolado de produção.
- Módulo Financeiro: fundação criada (`financeiro/`). Sem funcionalidade nova ainda.

---

## Versão Atual

**v0.6.1** — Gestão completa de entrega

---

## Funcionalidades Disponíveis

- Recebimento de foto e PDF via Telegram
- Seleção manual do tipo de documento antes da análise por IA
- Extração de dados por IA (Claude haiku-4-5) após tipo confirmado
- Edição de qualquer campo extraído antes de confirmar
- Seleção e correção manual de tipo e GGV
- Geração de PFM Word numerado (ex: GGV03-009)
- Salvamento automático do PFM na pasta OneDrive do GGV
- Criação de lançamento A PAGAR no banco
- Consulta de pedido digitando o código (ex: GGV03-009)
- Tela do pedido: dados financeiros, arquivos vinculados e histórico resumido
- Identificação de candidatos A PAGAR ao receber comprovante PIX
- Confirmação de pagamento com botões por candidato
- Marcação de lançamento como PAGO com gravação de valor, data e identificador
- Proteção contra duplo pagamento e reutilização do mesmo comprovante
- Recebimento e vinculação de NF-e ao pedido pago
- Revisão do Pedido de Compra com geração de arquivo rev01, rev02...
- Cockpit do pedido com número da NF-e, botões de comprovante e nota
- Registro de entrega: foto, /entrega, botão no cockpit, observação com sugestões
- Edição de entrega: mudar obs, trocar/remover foto, apagar entrega completa
- Modo teste isolado via `LAURA_ENV=test`

---

## Última Fiada Implementada

**Fase 6 — Fiada 6c+ — Gestão completa de entrega** *(2026-06-30)*

- Tela de gestão `✏️ Editar entrega` acessível pelo cockpit quando entrega registrada
- Mudar observação: seletor de obs com ← Voltar; suporta texto livre
- Trocar/anexar foto: substitui `doc_id_entrega` sem alterar obs ou data
- Remover foto: limpa só o documento, mantém obs e `entregue_em`
- Apagar entrega: zera obs + foto + data; cockpit volta a exibir `📦 Entregue`
- `📎 Foto / Documento` na tela de obs permite anexar antes de confirmar observação
- Cockpit: exibe `📦 Foto de entrega` + `✏️ Editar entrega` quando há obs e foto

---

**Fase 6 — Fiada 6c — Foto de Entrega e Registro de Entrega** *(2026-06-30)*

- Novo tipo de documento `foto_entrega` — sem análise Claude, vai direto à seleção do pedido
- `/entrega`: lista pedidos pendentes → seleciona → observação → grava
- Botão `📦 Entregue` no cockpit; vira `📦 Foto de entrega` quando foto vinculada
- Sugestões de observação: Completa · Parcial · Avaria · Produto diferente · Outra
- Colunas `doc_id_entrega`, `obs_entrega`, `entregue_em` em `lancamentos`

---

**Sprint de Experiência — Jeito da Laura** *(2026-06-30)*

- **Jeito da Laura** formalizado em `IDENTIDADE_DO_PRODUTO.md` e `PROCESSO.md` como princípio de comunicação assertiva; gatilho: "Esta mensagem resolve alguma coisa?"
- Revisão completa de todos os menus pelo Jeito da Laura

---

**Sprint de Experiência — Redesign de Cockpits** *(2026-06-30)*

- Cockpit do pedido: header compacto, financeiro consolidado, sem CNPJ/labels redundantes
- Botão PDF regenera via Playwright; histórico completo com entrega prevista e valor pago
- Cockpit da obra: header limpo, placeholder financeiro, CEP removido, botão Fechar
- Lista de pedidos da obra: tela própria via "📋 Pedidos", navegação direta ao pedido

---

**Fase 5 — Fiada 5a-1 — Categoria no Lançamento** *(2026-06-30)*

- `sugerir_categoria()` integrada ao fluxo do PFM em `bot.py`
- Tela de categoria exibida antes de gerar o pedido: sugestão com [✅ Confirmar] ou grade de seleção quando sem sugestão
- `registrar_lancamento()` e `gerar_pfm()` recebem `categoria` como parâmetro
- Categoria exibida na mensagem pós-PFM e na tela Financeiro do pedido
- Modo teste: deduplicação por `identificador_comprovante` bypassada (duas ocorrências)

---

**Fase 5 — Módulo Financeiro: Fiada 0 — Fundação** *(2026-06-30)*

- ADR-002 registrada: modularização incremental por domínio
- `financeiro/__init__.py` — docstring de contrato do domínio
- `financeiro/lancamento.py` — enums (`CategoriaLancamento`, `StatusLancamento`, `TipoDocumento`), `sugerir_categoria()`, `init_db_financeiro()`
- `financeiro/conciliacao.py` — esqueleto documentado (Fase 5d)
- `app/README.md` — elimina ambiguidade sobre uso da pasta `app/`
- `bot.py`: `init_db()` chama `init_db_financeiro(DB_PATH)` ao iniciar
- Colunas adicionadas em `lancamentos`: `categoria`, `tipo_documento`, `fonte_recurso`, `conciliado_em`

---

**Fase 4b — PC 2.0 parcial + Pendências de extração** *(2026-06-30)*

- PROMPT: 4 novos campos — `Ramo de atividade`, `Número do orçamento`, `Vendedor`, `Telefone do vendedor`
- `fornecedores`: coluna `ramo` adicionada; salva automaticamente ao gerar PFM
- `_gerar_html_pc()`: gera HTML do Pedido de Compra com dados reais
- `_html_para_pdf()`: converte HTML para PDF via Playwright Chromium
- Handler `pfm`: envia PDF em vez de DOCX
- Playwright instalado como nova dependência

---

**Fase 4a — Cadastro de Obras** *(2026-06-30)*

- Tabela `obras` substitui dicts hardcoded (`GGV_ENCARREGADO`, `GGV_DESC`, `GGV_ONEDRIVE`, `ENDERECOS`)
- Cockpit da obra: digitar `GGV03` abre o card com edição campo a campo
- `/nova_obra` para cadastrar novas obras conversacionalmente
- `/help`, comando desconhecido → `/help`, menu de comandos no Telegram

---

**v0.5.0 — Marcar como PAGO**

- `teclado_candidatos_pix()`: um botão `💳 Confirmar` por candidato encontrado
- Tela de confirmação final exibe comprovante × lançamento antes de gravar
- `UPDATE lancamentos SET status='pago' WHERE pfm_codigo=? AND status='a_pagar'`
- Campos gravados: `valor_pago`, `data_pagamento`, `doc_id_comprovante`, `identificador_comprovante`
- `ID da transação` como campo dedicado no PROMPT e em `parse_comprovante()`
- Proteção em duas camadas: rowcount no UPDATE + verificação por `identificador_comprovante`
- Colunas adicionadas via `ALTER TABLE` seguro

---

## Em Andamento

**Fase 4b — Pedido de Compra 2.0** *(aguarda validação)*

HTML→PDF implementado via Playwright Chromium. Precisa ser testado em produção com orçamento real.
O DOCX ainda é gerado em paralelo (salvo na pasta OneDrive). Remoção do Word fica para depois da validação.

**Fiada 6b — Recibo como Exceção** *(próxima)*

Recibo automático para fornecedores sem NF-e (`emite_nf = false`). Exceção registrada com motivo.

---

## Marcos do Produto

- **v0.1–0.3** — Fundação de engenharia: arquitetura, processo, documentação
- **v0.4–0.5** — Ciclo financeiro completo: orçamento → pedido → a pagar → pago
- **Sprint de Produto (2026-06-29)** — Identidade definida: quem a Laura é, o que ela promete, como ela fala
- **Sprint de Experiência Fase 2 (2026-06-29)** — Tela de validação do orçamento redesenhada; processo de desenvolvimento formalizado com Sessão de Produto e etapa 2.5

---

## Dívidas Técnicas Conhecidas

- `bot.py` monolítico com 3152 linhas — 50% acima do limite ADR-001 (~2000); refatoração prioritária na próxima sessão
- BD fornecedores: MO Construção com CNPJ errado; PRUDENTÓPOLIS com split incorreto
- `pfm_caminho` não existe como coluna — path reconstruído a cada consulta
- `gerar_pfm()` acumula responsabilidades: geração Word + gravação no banco + criação de lançamento
- `mime_type` não gravado no banco — inferido pela extensão do arquivo
- Deduplicação de comprovante por `identificador_comprovante` não atua quando Claude
  não extrai o ID da transação (comprovante sem número visível)

---

## Decisões Recentes

- **Obra vs. GGV (2026-06-29)** — "Obra" é o conceito; "GGV03" é o código da obra; "#GGV03-009"
  é o identificador público do Pedido de Compra. Interface usa "Obra GGV03"; banco mantém coluna
  `ggv` por compatibilidade. `pfm_codigo`, arquivos `.docx` e pastas existentes não serão alterados.
  Migração interna (`ggv` → `obra_codigo`) fica registrada como dívida futura de baixa prioridade.

- Tipo do documento é definido pelo usuário antes da IA — mais confiável e extensível
- `ID da transação` é a chave de deduplicação de comprovante, não o `obs` completo —
  mais curto e estável entre re-extrações do mesmo arquivo
- Proteção de pagamento em duas camadas: antes de listar candidatos + antes de gravar
- Modo teste implementado via variável de ambiente, não via comando Telegram — mais seguro

---

## Objetivo da Próxima Sessão

1. **Testar Fiada 6c em produção** — registro completo de entrega: foto, /entrega, edição, exclusão
2. **Refatorar bot.py** — 3152 linhas, 50% acima do limite ADR-001; iniciar extração de domínio `entrega/`
3. **Validar PC 2.0** — testar PDF com orçamento real; remover DOCX após validação

---

## Referência de Arquitetura

Arquitetura detalhada:
→ `docs/ARQUITETURA.md`

---

## Documentos Recomendados

- `docs/PROCESSO.md` — como conduzir uma sessão de desenvolvimento
- `docs/ROADMAP.md` — próximas fiadas e dívida técnica
- `CHANGELOG.md` — histórico completo de fiadas
- `docs/ARQUITETURA.md` — estrutura técnica atual

---

*Última atualização: 2026-06-30*
*Responsáveis: Dennis + Claude*
*Próxima revisão: ao final da próxima sessão*
