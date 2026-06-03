# Static Code Analyzer

## Project Overview

Static Code Analyzer is a web-based application developed using Python and Flask that analyzes C-like source code without executing it. The system performs Lexical Analysis, Syntax Analysis, and Semantic Analysis to identify programming errors at different stages of compilation.

The main objective of this project is to help students understand how compiler phases work internally and how errors can be detected before program execution.

---

## Features

* Tokenization of source code using a custom Lexer
* Detection of keywords, identifiers, literals, operators, and symbols
* Syntax error detection
* Missing semicolon detection
* Invalid declaration detection
* Invalid assignment detection
* Semantic error detection
* Undeclared variable checking
* Type mismatch checking
* User-friendly web interface using Flask
* Real-time analysis without code execution

---

## Technologies Used

* Python
* Flask
* HTML
* CSS
* Regular Expressions (Regex)

---

## System Workflow

1. User enters C-like source code in the web interface.
2. The Lexer converts source code into tokens.
3. The Syntax Analyzer validates program structure.
4. The Semantic Analyzer checks variable declarations and type compatibility.
5. Analysis results are displayed to the user.

### Flow Diagram

```text
User Code
    ↓
Lexer
    ↓
Token Stream
    ↓
Syntax Analyzer
    ↓
Semantic Analyzer
    ↓
Error Report
    ↓
Web Interface
```

---

## Project Structure

```text
Static-Code-Analyzer/
│
├── app.py
├── lexer.py
├── parser.py
├── semantic.py
├── templates/
│   └── index.html
├── static/
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/Coder-Priyan/Static-Code-Analyzer.git
cd Static-Code-Analyzer
```

### Install Dependencies

```bash
pip install flask
```

### Run Application

```bash
python app.py
```

### Open Browser

```text
http://127.0.0.1:5000
```

---

## Sample Input

```c
int a = 10;
int b = 20;
int sum = a + b;
```

---

## Sample Output

### Tokens

```text
(KEYWORD, int)
(IDENTIFIER, a)
(OPERATOR, =)
(NUMBER, 10)
```

### Syntax Errors

```text
No Syntax Errors Found
```

### Semantic Errors

```text
No Semantic Errors Found
```

---

## Learning Outcomes

* Understanding Compiler Design Fundamentals
* Lexical Analysis
* Syntax Analysis
* Semantic Analysis
* Token Generation
* Symbol Table Management
* Error Detection Techniques
* Flask Web Development

---

## Future Enhancements

* Support for complete C language syntax
* Abstract Syntax Tree (AST) generation
* Intermediate Code Generation
* Code Optimization Module
* Enhanced Error Reporting
* Multi-language Support

---

## Contributors

* Priyanshu Dangi

---

## License

This project is developed for educational and academic purposes.
