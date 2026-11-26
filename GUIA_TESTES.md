# Ronin Cyber Forge — Resumo do que foi feito + guia de testes

## 1. Resumo: o que foi feito e como

**Ponto de partida.** Li o `django.rar` (apps `app` e `login`) e comparei com o PDF. Faltavam Quem Somos, Produtos/Pedidos, recuperação de senha, Relatórios, editar integrante, proteção de acesso, e havia bugs (typos na API, filtros trocados, views de exclusão abertas a qualquer visitante, erro 500 para superusuário sem perfil).

**O que construí (mesmo projeto, tema Ronin Cyber Forge):**
| Parte | Como foi feito |
|---|---|
| Perfis | `login.Perfil` (administrador / funcionário / cliente) criado automaticamente por *signal* ao cadastrar qualquer usuário. Regras em `login/permissoes.py` (`@permissao_required('secao')`). |
| Login | `EntrarView`: admin → `/admin/`; demais → Dashboard (respeita `?next=` interno). |
| Cadastro / senha | Cadastro sempre cria **cliente**. Recuperação de senha com as views nativas do Django (4 telas + e-mail). |
| Produtos | Model `Produto` (veio de `Espada` do projeto antigo) + `Armeiro`. Cards com foto grande. API externa Open5e em `app/api_externa.py` (timeout, cache de 1h, não quebra se cair). |
| Compra | `Pedido`/`ItemPedido`. "Comprar" é POST só para logado, respeita estoque; "Finalizar" baixa o estoque em transação e congela o preço. |
| Equipe | CRUD completo no Supabase (`app/supabase_client.py`), cliente criado só no 1º uso e com erros tratados. |
| Serviços | Filtros combináveis, estatísticas, CRUD (exclusão só por POST), cliente só visualiza. |
| Relatórios | Agregações (`Count/Avg/Max/Min/Sum`) + 4 gráficos Chart.js + tabela resumo. |
| Visual | `style.css` único: preto/vermelho/roxo, neon, Orbitron/Rajdhani, scanlines, respeita `prefers-reduced-motion`. |
| Segurança | `DEBUG`/`SECRET_KEY`/hosts por variável de ambiente, cookies seguros e HTTPS em produção, CSRF, escape de HTML. |

**Como testei (rodei aqui, tudo passando): 87 testes automatizados** (`python manage.py test`):
- *27 funcionais* (`app/tests.py`): páginas públicas, redirecionamento por perfil, compra → finalizar → estoque, CRUDs, filtros, relatórios, CRUD da equipe com Supabase simulado (mock).
- *44 de segurança e robustez* (`app/tests_extra.py`):
  - **Autorização:** anônimo e cliente não alteram nada via POST; GET em rotas de exclusão = 405; CSRF obrigatório; API de categorias só escreve com staff.
  - **Escalada de privilégio:** cadastro e editar perfil ignoram `tipo_usuario`, `is_staff`, `is_superuser` e `username` enviados à força.
  - **Login:** senha errada, *open redirect* (`?next=https://evil.com`) bloqueado, logout só por POST, cliente não entra no `/admin/`.
  - **Senha:** fluxo completo de recuperação (e-mail → link → nova senha → login → token não reutilizável), e-mail inexistente não vaza, alterar senha.
  - **Pedidos:** isolamento entre usuários, estoque insuficiente quando 2 clientes disputam a última peça, preço congelado, produto inativo/inexistente.
  - **Entradas inválidas:** preço negativo/texto, e-mail inválido, filtros com `' OR 1=1` e `DROP TABLE`, id inexistente (404, nunca 500).
  - **XSS:** `<script>` em mensagem de contato, nome de produto, busca e dados vindos do Supabase saem escapados.
  - **Robustez:** Supabase sem chave/fora do ar, API Open5e com erro/JSON ruim, relatórios sem nenhum dado, seed idempotente, sem migrations pendentes.
- Também: subi o servidor com `DEBUG=False` (estáticos, mídia e páginas = 200) e rodei `check --deploy`.

**Bugs que os testes pegaram e eu corrigi:** a API aceitava categoria sem nome; avisos de cookies/HTTPS do `check --deploy`.

**Limites honestos:** os testes do Supabase, da API externa e do e-mail usam *mock* (provam a lógica, não a conexão real). Não abri navegador, então o visual e o Chart.js precisam do seu olho.

---

## 2. Guia: testes que você precisa fazer (eu não consigo)

### A) Supabase (banco remoto)
1. supabase.com → seu projeto → **SQL Editor** → cole e rode `supabase_setup.sql` (cria `integrantes` + políticas RLS + 2 linhas de exemplo).
2. Confirme no `.env`: `SUPABASE_URL` e `SUPABASE_KEY` (chave *publishable/anon*, em Settings → API).
3. `python manage.py runserver` e teste, nesta ordem:
   - `/quem-somos/` → aparecem os integrantes (se aparecer o aviso amarelo, a conexão falhou).
   - Entre como `funcionario` → Dashboard → **Equipe** → *Novo integrante* → salvar → conferir no Table Editor do Supabase.
   - *Editar* (muda o cargo) e *Excluir* (confirma e some).
4. **Erros comuns:** `new row violates row-level security policy` = faltaram as policies do SQL; `Invalid API key` = chave errada no `.env`; tabela vazia = cadastre integrantes pela tela de Equipe.

### B) API externa (Open5e)
1. Teste a API no terminal: `curl "https://api.open5e.com/v2/weapons/?limit=3"` — veja se retorna JSON com `results` e campos como `name`, `damage_dice`, `weight`, `cost`.
2. Abra `/produtos/`: a seção "Armas do mundo" deve mostrar cards. Se vier "indisponível", a URL mudou ou a rede bloqueou.
3. Se os campos forem outros, ajuste só o dicionário em `app/api_externa.py` (linhas com `a.get("...")`). Para outra API, troque `API_ARMAS_URL` no `.env`.

### C) E-mail (recuperar senha)
1. Gmail → conta Google → Segurança → verificação em 2 etapas → **Senhas de app** → gere uma.
2. No `.env`: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (senha de app), `DEFAULT_FROM_EMAIL`.
3. Teste rápido: `python manage.py shell` → `from django.core.mail import send_mail; send_mail("teste","oi","seuemail@gmail.com",["seuemail@gmail.com"])`.
4. Fluxo real: `/login/` → *Esqueceu a senha?* → e-mail de um usuário **que tenha esse e-mail cadastrado** → abra o link recebido → nova senha → entre. (Sem SMTP o e-mail só aparece no terminal do servidor.)
5. Depois de hospedar, confirme que o link do e-mail usa o **domínio do site**, não `localhost`.

### D) Visual no navegador (checklist, ~10 min)
- [ ] Fontes carregaram (títulos em Orbitron) e o neon/animações aparecem; abra o preview que fiz para comparar.
- [ ] Home, Quem Somos, Produtos, Contato, Entrar: sem elementos quebrados; menu correto.
- [ ] Cards de produto: foto grande; produtos sem foto mostram a espada 🗡️.
- [ ] Relatórios: os 4 gráficos desenham (precisa de internet para o Chart.js do CDN).
- [ ] Celular: F12 → ícone de dispositivo → iPhone/Android; menu e tabelas rolam sem quebrar.
- [ ] Teclado: Tab chega nos botões com foco visível.

### E) Roteiro ponta a ponta (use na apresentação)
1. **Visitante:** Home → Produtos (clique "Entrar p/ comprar" → vai pro login) → Contato (envie uma mensagem).
2. **Novo usuário:** Entrar → *Novo usuário* → cadastre → entre → cai no Dashboard (só 3 seções).
3. **Cliente:** Produtos → *Comprar* → Meus Pedidos → *Finalizar* → veja no histórico → confira o estoque diminuir.
4. **Cliente tentando burlar:** cole `/painel/relatorios/` na barra → deve voltar ao Dashboard com aviso.
5. **Funcionário** (`/admin/` → Perfis → mude o perfil do usuário): vê as 6 seções; leia/exclua mensagem em Contatos; crie/edite/exclua serviço; veja Relatórios; CRUD de Equipe.
6. **Admin:** ao entrar vai direto para `/admin/`; cadastre um produto novo com foto e veja aparecer em Produtos.

### F) Hospedagem e pós-deploy (PythonAnywhere)
1. Siga o README (clone/upload → venv → `pip install -r requirements.txt` → `.env` → `migrate`, `seed`, `collectstatic` → aba Web com WSGI `projeto.wsgi` e mapeamentos `/static/` → `.../staticfiles`, `/media/` → `.../media`).
2. No `.env` de produção: `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` longa e aleatória, `DJANGO_ALLOWED_HOSTS=seuusuario.pythonanywhere.com`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://seuusuario.pythonanywhere.com`. Se o login falhar por cookie/redirect infinito, confirme o HTTPS (ou `DJANGO_HTTPS=False` só como último recurso).
3. Depois de publicar, teste do **celular, em outra rede**: abrir o link, CSS carregado, imagens dos produtos aparecendo, login, compra, contato, recuperação de senha por e-mail, `/admin/`.
4. **Troque as senhas do seed** (`admin`, `funcionario`, `cliente` = `ronin@2026`) ou apague esses usuários e use `python manage.py createsuperuser`.
5. Rode `python manage.py check --deploy` no servidor: deve sobrar só avisos de HSTS opcionais.

### G) Antes de entregar (26/11/2026)
- [ ] Link do site funcionando e anotado.
- [ ] Integrantes reais no Supabase.
- [ ] Fotos nos produtos (via `/admin/` → Produtos).
- [ ] Senhas do seed trocadas e `.env` **fora** do que for enviado/versionado.
- [ ] Passou o roteiro da seção E no site hospedado.
