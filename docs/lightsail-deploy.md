# Deploy do backend no Lightsail

Este repositório usa o workflow [`deploy-lightsail.yml`](../.github/workflows/deploy-lightsail.yml) para
compilar o backend Java, enviar o artefato para a instância e reiniciar o serviço
systemd remoto.

## Segredo `LIGHTSAIL_SUDO_PASSWORD`

O passo final de deploy executa alguns comandos com `sudo`. Existem duas maneiras
suportadas para que eles funcionem:

1. **`sudo` sem senha para o usuário `deploy`**
   Execute o script [`vps/preparar_vps.sh`](../vps/preparar_vps.sh) com privilégio
   de `root`. Ele cria o arquivo `/etc/sudoers.d/deploy` permitindo que o usuário
   `deploy` rode `install`, `mv` e `systemctl` sem senha (detectando
   automaticamente o caminho real do binário), solução recomendada
   quando não for possível armazenar a senha no GitHub Secrets (por exemplo,
   quando o valor contém caracteres especiais ou a política da organização
   proíbe o compartilhamento da senha). O script valida o arquivo com `visudo`
   automaticamente.

   Caso prefira executar manualmente, replique o conteúdo abaixo e ajuste o
   usuário conforme necessário:

   ```bash
   # Conecte via SSH com um usuário que tenha permissão de `sudo`
   SYSTEMCTL_BIN="$(command -v systemctl)"
   sudo tee /etc/sudoers.d/deploy <<EOF
deploy ALL=(ALL) NOPASSWD: /usr/bin/install, /usr/bin/mv, ${SYSTEMCTL_BIN}
EOF
   sudo chmod 440 /etc/sudoers.d/deploy
   sudo visudo -cf /etc/sudoers.d/deploy
   ```

   Depois disso, teste manualmente com `sudo -n systemctl status
   sisacao-backend.service`. Se o comando funcionar sem solicitar senha, o
   workflow poderá executar os passos de deploy sem depender de nenhum segredo.

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

> 💡 O script [`vps/preparar_vps.sh`](../vps/preparar_vps.sh) já utiliza o
> `EMPRESA_SLUG=sisacao` por padrão, criando as pastas `/opt/sisacao/...`
> esperadas pelo workflow. Ajuste a variável apenas se realmente precisar de
> outro diretório e não se esqueça de atualizar o pipeline em conjunto.
