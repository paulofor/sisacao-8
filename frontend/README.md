# Frontend

Aplicação web responsável por acompanhar as coletas de dados enviadas ao BigQuery. A primeira tela implementada apresenta as
mensagens geradas pelas pipelines de ingestão, permitindo filtrar por severidade e pesquisar por coletor, dataset ou descrição.

## Estrutura

```
frontend/
├── README.md            # Este arquivo
└── app/                 # Projeto React (Vite + TypeScript)
    ├── .env.example     # Variáveis de ambiente do frontend
    ├── package.json     # Scripts e dependências
    └── src/             # Código-fonte da aplicação
```

## Como executar localmente

1. Configure as variáveis de ambiente copiando o arquivo de exemplo:

   ```bash
   cp app/.env.example app/.env.local
   ```

   Ajuste `VITE_API_BASE_URL` para o endpoint do backend que expõe as mensagens da coleta (por padrão `http://localhost:8080`).

2. Instale as dependências:

   ```bash
   cd app
   npm install
   ```

3. Suba o servidor de desenvolvimento:

   ```bash
   npm run dev
   ```

   O projeto ficará disponível em `http://localhost:5173` com hot reload habilitado.

4. Execute a build de produção (opcional):

   ```bash
   npm run build
   ```

## Próximos passos

- Integrar com os endpoints reais do backend (Spring Boot) que consultarão o BigQuery.
- Acrescentar autenticação, paginação e exportação de relatórios.
- Evoluir o design system e documentar componentes compartilháveis.

