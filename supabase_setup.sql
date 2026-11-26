-- Rode no SQL Editor do Supabase (banco REMOTO do projeto).
create table if not exists public.integrantes (
  id bigint generated always as identity primary key,
  nome text not null,
  cargo text not null,
  biografia text,
  foto_url text
);

alter table public.integrantes enable row level security;

-- O site usa a chave publicável (anon): libere leitura e escrita.
-- (Para um projeto acadêmico isto basta; em produção real restrinja a escrita.)
create policy "leitura publica" on public.integrantes for select using (true);
create policy "insercao" on public.integrantes for insert with check (true);
create policy "atualizacao" on public.integrantes for update using (true) with check (true);
create policy "exclusao" on public.integrantes for delete using (true);

insert into public.integrantes (nome, cargo, biografia) values
  ('Pedro', 'Mestre Armeiro', 'Responsável pela forja digital e pelo catálogo de lâminas.'),
  ('Integrante 2', 'Gerente de Vendas', 'Cuida do atendimento e dos pedidos dos clientes.');
