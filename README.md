⚔️ Ronin Cyber Forge

Loja de espadas com tema cyberpunk / samurai (preto, vermelho e roxo, com efeitos neon), desenvolvida em Django como Projeto Final da disciplina Desenvolvimento Web III — FATEC Praia Grande (DSM).

🌐 Site no ar: https://pedrobrinkdev.pythonanywhere.com

📌 Sobre o projeto

Sistema web com catálogo de espadas, compra por clientes autenticados, painel interno para a equipe da loja (serviços, contatos, equipe e relatórios) e dois bancos de dados:

Banco	Tecnologia	Uso
Local	SQLite (Django ORM)	Usuários, perfis, produtos, serviços, contatos e pedidos
Remoto	Supabase (PostgreSQL)	Integrantes da equipe (páginas Quem Somos e Equipe)

Também consome uma API externa (Open5e) para exibir armas de consulta na página de produtos.

✅ Funcionalidades (conforme o enunciado)

Páginas públicas

Home: apresentação do sistema, destaques do arsenal e menu (Quem Somos, Produtos, Contato, Entrar).
Quem Somos: texto institucional + integrantes consultados no Supabase.
Produtos: espadas cadastradas no banco local (com botão Comprar, só para usuários logados) e armas obtidas da API externa (somente consulta).
Contato: formulário aberto a visitantes, sem necessidade de login.
Entrar: login, Novo Usuário (cadastro) e Esqueceu a Senha (recuperação nativa do Django, com e-mail e link com token).

Área logada (Dashboard)

Menu com Dashboard, Voltar ao site e Sair; nome e perfil do usuário no topo.
Editar Perfil + Alterar Senha.
Contatos: ver e excluir as mensagens recebidas.
Serviços: listagem com filtros combináveis (busca, categoria, faixa de preço, situação, ordenação), estatísticas, adicionar, editar e excluir.
Equipe: CRUD completo dos integrantes no Supabase.
Meus Pedidos: carrinho, remoção de itens, finalização (baixa o estoque) e histórico.
Relatórios: indicadores e 4 gráficos (Chart.js), com filtro por categorias e escolha de quais gráficos exibir.
🔐 Perfis e permissões
Perfil	Ao entrar	Acesso
Administrador	Vai direto para o painel /admin/ do Django	Tudo (inclui cadastrar produtos, armeiros e pedidos)
Funcionário	Dashboard	Perfil, Contatos, Serviços (CRUD), Equipe, Meus Pedidos e Relatórios
Cliente (padrão no cadastro)	Dashboard	Perfil, Serviços (somente leitura) e Meus Pedidos

Todo cadastro novo nasce como Cliente. O perfil só é alterado por um administrador em /admin/ → Perfis.

🛠️ Tecnologias
Python 3.12 · Django 6 · Django REST Framework
SQLite (local) · Supabase / PostgreSQL (remoto)
HTML, CSS e JavaScript puros · Chart.js
WhiteNoise (arquivos estáticos) · python-dotenv
Hospedagem: PythonAnywhere
📁 Estrutura
ronin/
├── app/              # produtos, pedidos, serviços, contatos, equipe, relatórios
├── login/            # perfis, permissões, login, cadastro e recuperação de senha
├── projeto/          # configurações do Django (settings, urls, wsgi)
├── media/            # fotos dos produtos
├── manage.py
├── requirements.txt
├── supabase_setup.sql
└── .env.example
🚀 Como rodar localmente (Windows / PowerShell)
powershell
# 1) baixar o projeto
git clone https://github.com/pedrobrinkdev/Ronin_Cyber_forge.git ronin
cd ronin

# 2) criar e ativar o ambiente virtual
python -m venv venv
Set-ExecutionPolicy -Scope Process Bypass
venv\Scripts\Activate.ps1

# 3) instalar as dependências
pip install -r requirements.txt

# 4) criar o arquivo .env (veja a seção abaixo)
Copy-Item .env.example .env
notepad .env

# 5) criar o banco e os dados de exemplo
python manage.py migrate
python manage.py seed

# 6) iniciar o servidor
python manage.py runserver

Acesse http://127.0.0.1:8000.

O comando seed cria categorias, serviços, armeiros, produtos e os usuários de demonstração admin, funcionario e cliente. A senha deles é definida com python manage.py seed --senha SuaSenhaAqui (o padrão é só para uso local — troque em produção).

⚙️ Variáveis de ambiente (.env)

O arquivo .env não é enviado ao GitHub. Para rodar localmente, basta:

SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=sua-chave-publishable

Em produção, adicione também:

DJANGO_DEBUG=False
DJANGO_SECRET_KEY=uma-chave-longa-e-aleatoria
DJANGO_ALLOWED_HOSTS=seuusuario.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://seuusuario.pythonanywhere.com

Para o e-mail de recuperação de senha chegar de verdade, configure EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER e EMAIL_HOST_PASSWORD (veja o .env.example). Sem isso, o e-mail é apenas exibido no terminal.

🗄️ Configuração do Supabase
No painel do Supabase, abra SQL Editor.
Cole o conteúdo de supabase_setup.sql e execute. Ele cria a tabela integrantes, as políticas de acesso e dois registros de exemplo.
Em Project Settings → API Keys, copie a Publishable key e a Project URL para o .env.
🧪 Testes
powershell
python manage.py test

São 87 testes automatizados, cobrindo páginas públicas, autenticação, permissões por perfil, compra e estoque, CRUDs, relatórios com filtros, avisos ao usuário e segurança (CSRF, XSS, escalada de privilégio, redirecionamento malicioso e entradas inválidas). O Supabase e a API externa são simulados (mock) nos testes.

☁️ Deploy (PythonAnywhere)
git clone do repositório no console Bash e criação do ambiente virtual.
pip install -r requirements.txt e criação do .env de produção.
python manage.py migrate, python manage.py seed --senha ... e python manage.py collectstatic --noinput.
Web app com Manual configuration, apontando Source code, Virtualenv e o arquivo WSGI.
Arquivos estáticos: /static/ → .../ronin/staticfiles e /media/ → .../ronin/media.
Reload na aba Web.

Para publicar atualizações: git push no computador, git pull no console do servidor e Reload.

🔒 Segurança
DEBUG, SECRET_KEY e hosts configurados por variáveis de ambiente.
Cookies seguros e redirecionamento para HTTPS em produção.
Proteção CSRF em todos os formulários; exclusões e compras apenas por POST.
Escape automático de HTML nos templates (proteção contra XSS).
Cadastro sempre cria o perfil Cliente; privilégios não podem ser enviados pelo formulário.
👤 Autor

Pedro Brinkmann — FATEC Praia Grande · Desenvolvimento de Sistemas e Mídias Digitais (DSM) GitHub: @pedrobrinkdev

Projeto acadêmico — Desenvolvimento Web III, entrega em 26/11/2026.
