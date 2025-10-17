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
   Em produção, o valor padrão passa a ser `"/api"`, pois o nginx configurado via `vps/preparar_vps.sh`
   cria um proxy reverso para o backend.

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

## Deploy automático (Lightsail)

- Execute o script [`vps/preparar_vps.sh`](../vps/preparar_vps.sh) na VPS para provisionar nginx,
  criar o usuário `deploy` e preparar os diretórios `/opt/sisacao/app/frontend` e
  `/home/deploy/sisacao/frontend` utilizados durante o deploy.
- A _workflow_ [`deploy-frontend-lightsail.yml`](../.github/workflows/deploy-frontend-lightsail.yml)
  é disparada em pushes para a branch `master` que alterem arquivos dentro de `frontend/` (ou quando
  acionada manualmente) e realiza o _build_ com `npm run build`.
- O artefato gerado é publicado via `scp` para a VPS e movido para `/opt/sisacao/app/frontend`,
  ficando imediatamente disponível através do nginx em `http://<IP-da-VPS>/`.

