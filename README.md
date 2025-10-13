Livro Caixa - Sistema Financeiro
Um sistema web completo para gestão financeira pessoal, desenvolvido com Flask. Permite o controle de receitas e despesas, visualização de dashboards interativos, geração de relatórios detalhados, e funcionalidades avançadas como reconhecimento de valores em comprovantes via OCR.

✨ Principais Funcionalidades
Autenticação de Usuários: Sistema seguro de login e cadastro para proteger seus dados financeiros.

Dashboard Intuitivo: Visualize um resumo de suas finanças com cards de receitas, despesas e saldo, além de gráficos interativos sobre a evolução mensal e distribuição por categoria.

Lançamento de Transações: Adicione receitas e despesas de forma rápida e detalhada, informando descrição, valor, data, categoria e forma de pagamento.

Anexos com OCR: Anexe comprovantes (imagens ou PDFs) às suas transações. O sistema utiliza OCR (Reconhecimento Óptico de Caracteres) para extrair e preencher automaticamente o valor do documento.

Relatórios Detalhados: Gere relatórios financeiros filtrando por período e tipo de transação (receita ou despesa). Exporte os relatórios para PDF ou imprima-os diretamente.

Importação em Lote: Importe múltiplas transações de uma só vez enviando uma planilha Excel (.xlsx).

Tema Claro e Escuro: Alterne entre os temas para uma melhor experiência de visualização.

Backup: Faça o download do banco de dados completo com um único clique para garantir a segurança dos seus dados.

📸 Screenshots
Login	Dashboard	Lançamentos
<img src="artenioreis/livro_caixa/livro_caixa-bbbdd6e8fd9c977eabb8c5461f9ddf54624821f8/static/images/santa_teresinha.webp" width="250">	
<img src="artenioreis/livro_caixa/livro_caixa-bbbdd6e8fd9c977eabb8c5461f9ddf54624821f8/uploads/Agua_e_Esgoto.jpg" width="250">	
<img src="artenioreis/livro_caixa/livro_caixa-bbbdd6e8fd9c977eabb8c5461f9ddf54624821f8/uploads/cupo2.jpg" width="250">

Exportar para as Planilhas
🛠️ Tecnologias Utilizadas
Backend
Python: Linguagem de programação principal.

Flask: Microframework web para a construção da API e da aplicação.

SQLite: Banco de dados relacional para armazenamento dos dados.

Pandas: Para importação de dados de planilhas Excel.

Pytesseract, Pillow & pdf2image: Bibliotecas para a funcionalidade de OCR.

ReportLab: Para a geração de relatórios em PDF.

Frontend
HTML5 & CSS3: Estruturação e estilização das páginas.

Bootstrap 5: Framework CSS para a criação de um design responsivo.

JavaScript (ES6): Para interatividade, manipulação do DOM e comunicação com a API.

Plotly.js: Biblioteca para a criação dos gráficos do dashboard.

🚀 Instalação e Execução
Siga os passos abaixo para executar o projeto localmente.

Pré-requisitos
Python 3.x

Pip (gerenciador de pacotes do Python)

Tesseract-OCR: É essencial para a funcionalidade de upload de comprovantes.

Instruções de instalação para Windows, Linux e macOS.

Passos
Clone o repositório:

Bash

git clone https://github.com/seu-usuario/livro_caixa.git
cd livro_caixa
Crie e ative um ambiente virtual:

Bash

# Para Windows
python -m venv venv
venv\Scripts\activate

# Para Linux/macOS
python3 -m venv venv
source venv/bin/activate
Instale as dependências:

Bash

pip install -r requirements.txt
Configure o Tesseract no app.py:
Abra o arquivo app.py e encontre a linha pytesseract.pytesseract.tesseract_cmd. Altere o caminho para o local onde o Tesseract foi instalado no seu sistema.

Python

# Exemplo para Windows:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Exemplo para Linux (geralmente não precisa se estiver no PATH):
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
Execute a aplicação:

Bash

python app.py
O servidor será iniciado. Acesse a aplicação no seu navegador através do endereço http://127.0.0.1:5000.

📖 Como Usar
Crie uma conta: Acesse a página de cadastro para criar seu usuário.

Faça o login: Utilize suas credenciais para acessar o sistema.

Explore o Dashboard: Tenha uma visão geral de suas finanças.

Adicione Transações: Vá para a página de "Lançamentos" para adicionar suas receitas e despesas. Experimente anexar um comprovante e veja o valor ser preenchido automaticamente.

Gere Relatórios: Na seção "Relatórios", filtre suas transações por data e tipo para uma análise mais profunda.
