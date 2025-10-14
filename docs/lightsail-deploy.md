# Deploy do backend no Lightsail

Este repositório usa o workflow [`deploy-lightsail.yml`](../.github/workflows/deploy-lightsail.yml) para
compilar o backend Java, enviar o artefato para a instância e reiniciar o serviço
systemd remoto.

## Segredo `LIGHTSAIL_SUDO_PASSWORD`

O passo final de deploy executa alguns comandos com `sudo`. Existem duas maneiras
suportadas para que eles funcionem:

1. **`sudo` sem senha para o usuário `deploy`**  
   Configure a instância para permitir que o usuário `deploy` execute os comandos
   necessários (`install`, `mv`, `systemctl`) sem senha, por exemplo adicionando
   uma entrada específica em `/etc/sudoers.d/`. Quando essa opção está ativa,
o workflow usa `sudo -n` e não precisa de nenhum segredo adicional.

2. **Senha armazenada no GitHub Secrets**  
   Caso a instância exija senha para `sudo`, crie o segredo
   `LIGHTSAIL_SUDO_PASSWORD` no repositório e armazene nele a senha do usuário
   `deploy`. O workflow envia o valor desse segredo para o `sudo -S`, evitando o
   prompt interativo que causava a falha observada originalmente.

> ℹ️  Não é necessário criar o segredo se você já configurou `sudo` sem senha.
> Caso contrário, o segredo é obrigatório para que o reinício do serviço seja
> concluído com sucesso.

## Checklist rápido

- [ ] Acesso SSH via chave (`secrets.KEY`) funcionando.
- [ ] Pasta `/home/deploy/sisacao/app/` existente na instância.
- [ ] Uma das opções acima configurada para permitir o uso de `sudo`.
- [ ] (Opcional) `journalctl -u sisacao-backend.service -f` disponível para
      depuração em deploys futuros.
