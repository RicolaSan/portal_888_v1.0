# Portal 888 v1.0

Portal web desenvolvido em Flask para gestão e controle de processos empresariais.

## Sobre o Projeto

Este é um sistema web desenvolvido em Flask que integra diferentes módulos de controle:

- **Controle de Vencimento**: Gestão de prazos e vencimentos
- **Controle de Perdas**: Monitoramento e análise de perdas
- **Controle de ISV**: Gestão de ISV (Imposto Sobre Vendas)

## Tecnologias Utilizadas

- **Python 3.x**
- **Flask 2.2.2** - Framework web
- **Pandas 1.5.3** - Manipulação de dados
- **SQLAlchemy 1.4.39** - ORM para banco de dados
- **Gunicorn 20.1.0** - Servidor WSGI
- **Flask-CORS 3.0.10** - Controle de CORS
- **Flask-Login 0.6.2** - Autenticação de usuários
- **Flask-WTF 1.0.0** - Formulários web

## Estrutura do Projeto

```
portal_888_v1.0/
├── flask-app/
│   ├── app/
│   │   ├── controle_de_isv/
│   │   ├── controle_de_perdas/
│   │   ├── controle_vencimento/
│   │   └── main/
│   ├── config.py
│   ├── requirements.txt
│   └── run.py
├── cores.css
├── .gitignore
└── README.md
```

## Instalação e Configuração

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passos para instalação

1. **Clone o repositório**
   ```bash
   git clone <url-do-repositorio>
   cd portal_888_v1.0
   ```

2. **Crie um ambiente virtual**
   ```bash
   python -m venv venv
   ```

3. **Ative o ambiente virtual**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. **Instale as dependências**
   ```bash
   cd flask-app
   pip install -r requirements.txt
   ```

5. **Execute a aplicação**
   ```bash
   python run.py
   ```

## Acesso

Após executar a aplicação, ela estará disponível em:
- **URL**: `http://10.122.244.64:5099`
- **Modo**: Debug habilitado

## Módulos do Sistema

### Controle de Vencimento
- Gestão de produtos próximos ao vencimento
- Relatórios de itens vencendo em 45 dias
- Controle de valores a vencer

### Controle de Perdas
- Monitoramento de perdas por grupo
- Análise de perdas por vencimento
- Controle de produtos em temperatura controlada (frios)
- Ajustes preventivos

### Controle de ISV
- Gestão de Imposto Sobre Vendas
- Processamento e controle fiscal

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está sob licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## Autor

Desenvolvido para o Portal 888 v1.0

---

**Nota**: Certifique-se de configurar adequadamente as variáveis de ambiente e conexões com banco de dados antes de executar em produção.