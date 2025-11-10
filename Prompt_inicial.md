Vamos trabalhar agora no desenvolvimento da DGTAX. eles precisam montar uma plataforma (inicialmente um POC, apenas em backend) que os usuários faram algumas perguntas sobre empresas e incentivos fiscais recebidos e deveremos utilizar a IA (Ollama, inicialmente) para  avaliar qual query será realizada no banco de dados (postgres), selecionar as empresas e mostrar os resultados. No arquivo @Perguntas e Respostas da IA DGTAX (Base 100+).docx  é um modelo de como as perguntas são feitas e como devem ser dadas as respostas. Fluxo principal:

Receber a pergunta
Enviar para IA (OLLAMA) ajustar a pergunta e pegar os dados da query para consulta no banco de dados e seleção das empresas conforme pergunta
Enviar essas empresas para que a IA faça modele a resposta utilizando os exemplos
Enviar retorno para usuário que perguntou


Abaixo estão as ddl das tabelas no postgres:
server: caitanserver:5432 (postgres)
user: admin
senha: admincaitan
banco: dgtax

Tabelas:
-- public.beneficios definição

-- Drop table

-- DROP TABLE public.beneficios;

CREATE TABLE public.beneficios (
	codigo_beneficio varchar(20) NOT NULL,
	descricao text NOT NULL,
	CONSTRAINT beneficios_pkey PRIMARY KEY (codigo_beneficio)
);


-- public.empresa definição

-- Drop table

-- DROP TABLE public.empresa;

CREATE TABLE public.empresa (
	id bigserial NOT NULL,
	cnpj varchar(14) NOT NULL,
	razao_social varchar(255) NULL,
	nome_fantasia varchar(255) NULL,
	data_fundacao date NULL,
	capital_social numeric(20, 2) NULL,
	natureza_juridica_id int4 NULL,
	natureza_juridica_descricao varchar(255) NULL,
	porte_id int4 NULL,
	porte_descricao varchar(50) NULL,
	situacao_cadastral_id int4 NULL,
	situacao_cadastral_descricao varchar(50) NULL,
	data_situacao_cadastral date NULL,
	matriz bool NULL,
	data_atualizacao timestamp NULL,
	jurisdicao varchar(50) NULL,
	simei_optante bool NULL,
	simples_optante bool NULL,
	logradouro text NULL,
	numero varchar(50) NULL,
	complemento text NULL,
	bairro varchar(100) NULL,
	codigo_municipio int4 NULL,
	cidade varchar(100) NULL,
	uf bpchar(2) NULL,
	cep varchar(8) NULL,
	codigo_pais int4 NULL,
	nome_pais varchar(100) NULL,
	telefones jsonb NULL,
	emails jsonb NULL,
	CONSTRAINT empresa_cnpj_key UNIQUE (cnpj),
	CONSTRAINT empresa_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_empresa_cnpj ON public.empresa USING btree (cnpj);


-- public.beneficio_empresa definição

-- Drop table

-- DROP TABLE public.beneficio_empresa;

CREATE TABLE public.beneficio_empresa (
	id serial4 NOT NULL,
	empresa_id int8 NOT NULL,
	periodo_apuracao int4 NULL,
	uf bpchar(2) NULL,
	dados jsonb NULL,
	CONSTRAINT beneficio_empresa_pkey PRIMARY KEY (id),
	CONSTRAINT fk_empresa FOREIGN KEY (empresa_id) REFERENCES public.empresa(id) ON DELETE RESTRICT
);


-- public.empresa_atividade definição

-- Drop table

-- DROP TABLE public.empresa_atividade;

CREATE TABLE public.empresa_atividade (
	id serial4 NOT NULL,
	empresa_id int8 NOT NULL,
	codigo_cnae int4 NULL,
	descricao_cnae text NULL,
	is_principal bool NOT NULL,
	CONSTRAINT empresa_atividade_pkey PRIMARY KEY (id),
	CONSTRAINT fk_empresa FOREIGN KEY (empresa_id) REFERENCES public.empresa(id) ON DELETE CASCADE
);


-- public.empresa_socio definição

-- Drop table

-- DROP TABLE public.empresa_socio;

CREATE TABLE public.empresa_socio (
	id serial4 NOT NULL,
	empresa_id int8 NOT NULL,
	identificador_pessoa_origem varchar(50) NULL,
	nome_socio varchar(255) NULL,
	tipo_pessoa varchar(20) NULL,
	documento_socio varchar(20) NULL,
	faixa_etaria varchar(20) NULL,
	data_entrada date NULL,
	codigo_qualificacao int4 NULL,
	descricao_qualificacao varchar(100) NULL,
	representante_nome varchar(255) NULL,
	representante_documento varchar(20) NULL,
	representante_qualificacao_id int4 NULL,
	representante_qualificacao_texto varchar(100) NULL,
	CONSTRAINT empresa_socio_pkey PRIMARY KEY (id),
	CONSTRAINT fk_empresa FOREIGN KEY (empresa_id) REFERENCES public.empresa(id) ON DELETE CASCADE
);


Aqui está a estrutura do json:
{"uf": "DF", "_id": {"$oid": "68e57b2e40cda0dc0b732894"}, "cnae": "ATIVIDADES DE SERVIÇOS FINANCEIROS", "ben 18": 0, "ben 23": 0, "ben 25": 0, "ben 26": 0, "ben 29": 0, "ben 30": 0, "ben 41": 0, "ben 47": 0, "ben 58": 0, "ben 60": 0, "ben 61": 0, "ben 64": 0, "ben 65": 0, "ben 66": 0, "ben 67": 0, "ben 68": 0, "ben 69": 0, "ben 70": 0, "ben 71": 0, "ben 72": 0, "ben 73": 0, "ben 74": 0, "ben 75": 0, "ben 76": 0, "ben 77": 0, "ben 78": 0, "ben 79": 0, "ben 80": 0, "ben 81": 0, "ben 82": 0, "ben 83": 0, "ben 84": 0, "ben 85": 0, "ben 86": 0, "ben 87": 0, "ben 88": 0, "ben 89": 53530871.4, "ben 90": 0, "ben 91": 0, "ben 92": 0, "ben 93": 0, "ben 94": 0, "ben 95": 0, "ben 103": 0, "ben 104": 0, "ben 105": 0, "ben 106": 0, "ben 107": 0, "ben 108": 0, "ben 109": 0, "ben 110": 0, "ben 111": 0, "ben 112": 0, "ben 113": 0, "ben 114": 0, "ben 115": 0, "ben 116": 0, "ben 117": 0, "ben 118": 0, "ben 119": 0, "ben 120": 0, "ben 121": 0, "ben 122": 0, "ben 123": 0, "ben 124": 0, "ben 125": 0, "ben 126": 0, "ben 127": 0, "ben 128": 0, "ben 129": 0, "ben 130": 0, "ben 131": 0, "ben 132": 0, "ben 133": 0, "ben 134": 0, "ben 135": 0, "ben 136": 0, "ben 137": 0, "ben 138": 0, "ben 139": 0, "ben 140": 0, "ben 141": 0, "ben 142": 0, "ben 143": 0, "ben 144": 0, "ben 145": 0, "ben 146": 0, "ben 147": 0, "cod_cnae": "64", "cnaeprincipal": "6422100"}


Tenho uma tabela chamada:
beneficio, essa tabela demonstra a descrição do benefício que está em beneficio_empresa através do "ben xx" que é a codificação interna do benefício.

Endereço do ollama:
host: caitanserver:5010

