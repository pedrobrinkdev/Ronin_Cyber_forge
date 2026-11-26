# Ronin Cyber Forge — WEB III (Django)

Loja de espadas cyberpunk/samurai. Banco **local** = SQLite (Django). Banco **remoto** = Supabase (tabela `integrantes`).

## Rodar local
```bash
python -m venv venv && venv\Scripts\activate      # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed            # dados de exemplo + usuários admin/funcionario/cliente (senha ronin@2026)
python manage.py runserver
python manage.py test            # 87 testes
```
No Supabase (SQL Editor) rode o arquivo `supabase_setup.sql` e mantenha `SUPABASE_URL` e `SUPABASE_KEY` no `.env`.

## Perfis e permissões
| Perfil | Ao entrar | Acesso |
|---|---|---|
| administrador | vai direto para `/admin/` | tudo (inclui cadastrar produtos, armeiros, pedidos) |
| funcionário | Dashboard | Perfil, Contatos, Serviços (CRUD), Equipe, Meus Pedidos, Relatórios |
| cliente (cadastro) | Dashboard | Perfil, Serviços (só leitura), Meus Pedidos |

Mude o perfil de um usuário em `/admin/` → Perfis.

## Hospedagem (PythonAnywhere, grátis)
1. Suba o projeto (git clone ou upload do zip) e crie um virtualenv: `pip install -r requirements.txt`.
2. Crie o `.env` a partir de `.env.example` (DEBUG=False, ALLOWED_HOSTS com o seu domínio).
3. `python manage.py migrate && python manage.py seed && python manage.py collectstatic`.
4. Aba **Web** → Manual config → aponte o WSGI para `projeto.wsgi`; Static files: `/static/` → `.../staticfiles`, `/media/` → `.../media`.
5. Reload. **Troque as senhas do seed** (ou crie seu superuser com `createsuperuser`).

## Observações
- Catálogo externo (Produtos): API Open5e (`API_ARMAS_URL` no `.env`). Se estiver fora do ar a página continua funcionando.
- Fotos dos produtos novos: cadastre em `/admin/` → Produtos (upload de imagem).
