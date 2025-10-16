# Monitoramento das Coletas

Interface web construída com React, Vite e Material UI para acompanhar as mensagens produzidas pelas pipelines de ingestão que
gravam dados no BigQuery.

## Principais recursos

- Listagem das mensagens de coleta ordenadas por data/hora.
- Filtro por severidade (todas, sucesso, info, alerta, erro e crítico).
- Busca textual por coletor, dataset ou conteúdo da mensagem.
- Atualização manual e automática (a cada 60s) via React Query.

## Configuração

1. Copie o arquivo `.env.example` para `.env.local` e ajuste a URL base da API:

   ```bash
   cp .env.example .env.local
   ```

2. Garanta que as dependências estão instaladas (`npm install`).

3. Rode o servidor local:

   ```bash
   npm run dev
   ```

   O frontend utilizará o valor de `VITE_API_BASE_URL` para buscar `GET /data-collections/messages`. O endpoint deve retornar um
   array ou um objeto com a propriedade `items`, cada item representando uma mensagem.

4. Para gerar a build de produção utilize `npm run build`. O resultado ficará disponível na pasta `dist/`.

## Estrutura relevante

```
src/
├── api/                         # Clientes HTTP e contratos de dados
├── components/                  # Componentes visuais reutilizáveis
├── hooks/                       # Hooks customizados (React Query)
├── theme.ts                     # Tema do Material UI
├── App.tsx                      # Página principal com filtros e tabela
└── index.css                    # Estilos globais
```

## Integração com o backend

O frontend espera que o backend expose o endpoint `GET /data-collections/messages`, com suporte opcional aos parâmetros
`severity`, `collector` e `limit`. Campos adicionais retornados pela API são exibidos na coluna de metadados.

