# Guia de troubleshooting – appleboy/scp-action

Este guia ajuda a resolver o erro observado no GitHub Actions durante o passo de deploy com `appleboy/scp-action@v0.1.7`:

```
ssh.ParsePrivateKey: ssh: no key found
...
error copy file to dest: dial tcp <HOST>:22: i/o timeout
```

## 1. Verifique o segredo `LIGHTSAIL_SSH_KEY`

1. Gere (ou recupere) uma chave SSH sem frase de acesso (`passphrase`):
   ```bash
   ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/lightsail_deploy
   ```
2. Adicione a **chave pública** (`lightsail_deploy.pub`) ao arquivo `~/.ssh/authorized_keys` do servidor Lightsail.
3. Copie o conteúdo completo da **chave privada** (`lightsail_deploy`) e grave em um segredo do GitHub chamado `LIGHTSAIL_SSH_KEY` (Settings → Secrets → Actions).
   - Cole exatamente como está, incluindo o bloco `-----BEGIN OPENSSH PRIVATE KEY-----` e as quebras de linha.
   - Não deixe o segredo em branco e nem substitua por uma chave pública.

> O erro `ssh.ParsePrivateKey: ssh: no key found` indica que o segredo atual está vazio, truncado ou contém uma chave no formato errado.

## 2. Confirme os parâmetros do workflow

O workflow `.github/workflows/deploy-lightsail.yml` utiliza os valores embutidos abaixo:

- Host: `172.26.8.107`
- Usuário SSH: `ubuntu`

Garanta que esses dados continuam válidos para a instância que receberá o deploy.

## 3. Teste o acesso SSH manualmente

No seu ambiente local, rode:
```bash
ssh -i ~/.ssh/lightsail_deploy <usuario>@<host>
```
Se o login falhar localmente, ajuste permissões de arquivos (`chmod 600 ~/.ssh/lightsail_deploy`) ou verifique se a chave pública foi adicionada corretamente no servidor.

## 4. Libere o tráfego na porta 22

O segundo erro (`dial tcp ...:22: i/o timeout`) acontece quando o GitHub Actions não consegue abrir a conexão SSH. Confirme:

- Regras de firewall / Lightsail permitem acesso SSH (porta 22) para endereços externos.
- O servidor está ligado e aceitando conexões.
- Não existe bloqueio por fail2ban ou configurações de segurança adicionais.

## 5. Re-execute o workflow

Depois de ajustar as credenciais e validar o acesso, execute novamente o workflow `Deploy backend to Lightsail` via `workflow_dispatch` ou realizando um novo push na branch `master`.

Se ainda houver falhas, habilite o modo debug do action adicionando `debug: true` ao passo do `appleboy/scp-action` para obter mais detalhes.

