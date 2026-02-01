# 📦 Nome do Pacote

Pequena descrição do que o pacote faz.
Exemplo: *Um utilitário para monitoramento de PVs EPICS com envio de alertas por e-mail.*

---

## 🚀 Instalação

Se o pacote estiver publicado no PyPI:

```bash
pip install nome-do-pacote
```

Ou, se estiver localmente:

```bash
pip install .
```

Ou diretamente via repositório:

```bash
pip install git+https://github.com/usuario/repositorio.git
```

---

## 🧱 Estrutura do Projeto

Exemplo de estrutura comum:

```
nome_do_pacote/
│── src/nome_do_pacote/
│   ├── __init__.py
│   ├── core.py
│   └── utils.py
│── tests/
│── pyproject.toml
│── README.md
│── LICENSE
```

---

## ⚙️ Sobre o `pyproject.toml`

O arquivo `pyproject.toml` define as configurações do pacote.
Exemplo básico usando o padrão **PEP 621 + setuptools**:

```toml
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "nome-do-pacote"
version = "0.1.0"
description = "Descrição curta do pacote"
authors = [{ name = "Seu Nome", email = "email@example.com" }]
license = { text = "MIT" }
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "requests",
    "numpy>=1.20"
]

[project.scripts]
nome-comando = "nome_do_pacote.core:main"
```

Se estiver usando **Poetry**, seria:

```toml
[tool.poetry]
name = "nome-do-pacote"
version = "0.1.0"
description = "Descrição do pacote"
authors = ["Seu Nome <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.8"
requests = "*"

[tool.poetry.scripts]
nome-comando = "nome_do_pacote.core:main"
```

---

## 🧪 Como Rodar os Testes

```bash
pytest
```

Ou com cobertura:

```bash
pytest --cov=nome_do_pacote
```


